import sqlite3
import os
import json
import time
from google import genai
from google.genai import types 
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

API_BATCH_INTERVAL = 5400   # Interval between large batch API calls (90 minutes)
POLLING_INTERVAL = 15       # Main loop sleep interval
MSG_LIMIT = 200             # Max number of logs processed per batch
IMG_LIMIT = 50              # Max number of images sent to the model per batch

def process_logs_large_batch():
    """
    Fetches unprocessed logs from the database, bundles them into a single
    multi-part request, sends them to Gemini for moderation analysis,
    and writes the results back into the database.
    """
    conn = sqlite3.connect('monitor.db')
    c = conn.cursor()

    # Fetch unprocessed logs up to MSG_LIMIT
    c.execute(f"""
        SELECT id, content, attachment_url, target_content, target_attachment_url 
        FROM logs WHERE processed = 0 LIMIT {MSG_LIMIT}
    """)
    rows = c.fetchall()
    
    if not rows:
        conn.close()
        return

    print(f"[{time.strftime('%H:%M:%S')}] {len(rows)}件のログを収集。一括解析を開始するね。")
    
    # Build the multi-part prompt for Gemini
    parts = ["Analyze the following Discord logs for community moderation. Return ONLY a JSON array of results."]
    img_count = 0
    
    for r in rows:
        row_id, content, img_path, t_content, t_img_path = r

        # Add text content for this log entry
        parts.append(f"\n[ID: {row_id}]\nReply: '{content}'\nContext: '{t_content}'")
        
        # Attach images if available and within IMG_LIMIT
        if img_count < IMG_LIMIT:
            for p in [t_img_path, img_path]:
                if p and isinstance(p, str) and os.path.exists(p) and img_count < IMG_LIMIT:
                    try:
                        img = Image.open(p)
                        parts.append(f"Image for ID {row_id}:")
                        parts.append(img)  # PIL image object is passed directly
                        img_count += 1
                    except:
                        pass
    
    # Specify strict output format for the model
    parts.append(f"""
    \nOutput format: A JSON array of exactly {len(rows)} objects. 
    Keys: "id", "offensive"(0-10), "rebuke"(0-10), "summary"(English), "punish"(0:Safe, 1:ToxicText, 2:NSFWImage).
    """)

    try:
        # Send the batch request to Gemini
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite', 
            contents=parts,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                max_output_tokens=8192  # Large output limit for big batches
            )
        )
        
        # Parse JSON returned by the model
        results = json.loads(response.text)
        
        # Write results back into the database
        for res in results:
            c.execute("""
                UPDATE logs SET 
                    offensive_score = ?, rebuke_score = ?, 
                    summary = ?, processed = 1, bot_replied = ? 
                WHERE id = ?
            """, (
                res['offensive'], res['rebuke'], res['summary'], 
                res.get('punish', 0), res['id']
            ))
        conn.commit()
        print(f"✅ {len(results)}件のバッチ解析完了、画像処理数は: {img_count} 件だよ。")
        
    except Exception as e:
        # Catch any model or JSON parsing errors
        print(f"バッチ解析エラーが発生したみたい: {e}")

    conn.close()

def sync_human_reviews():
    """
    Syncs manual moderator decisions with the automated system.
    If a human moderator marked a log as 'Toxic (NG)', the bot immediately
    assigns a punishment level based on whether an image was included.
    """
    conn = sqlite3.connect('monitor.db')
    c = conn.cursor()
    
    c.execute("""
        SELECT id, attachment_url, target_attachment_url 
        FROM logs WHERE human_review_status = 'Toxic (NG)' AND bot_replied = 0
    """)
    manual_targets = c.fetchall()
    
    if manual_targets:
        for mid, img, timg in manual_targets:
            # Determine punishment level: 2 if image exists, otherwise 1
            has_img = (isinstance(img, str) and img) or (isinstance(timg, str) and timg)
            p_level = 2 if has_img else 1
            c.execute("UPDATE logs SET bot_replied = ? WHERE id = ?", (p_level, mid))
            print(f"管理者による即時粛清を検知したよ: ID {mid} (Level {p_level})")
        conn.commit()
    conn.close()

def generate_hourly_report():
    """
    Generates a 24-hour moderation summary using Gemini and stores it
    in the 'reports' table.
    """
    conn = sqlite3.connect('monitor.db'); c = conn.cursor()

    query = """
        SELECT user_name, target_user_name, COUNT(*), 
               AVG(offensive_score), AVG(rebuke_score)
        FROM logs 
        WHERE processed = 1 AND created_at > DATETIME('now', '-24 hours') 
        GROUP BY user_name, target_user_name
    """
    c.execute(query); stats = c.fetchall()

    if stats:
        try:
            # Ask Gemini to summarize the stats
            res = client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=f"Summarize server health stats: {str(stats)}"
            )
            c.execute("INSERT INTO reports (report_text) VALUES (?)", (res.text,))
            conn.commit()
            print("レポートを更新したよ")
        except:
            pass
    conn.close()

def cleanup_db():
    """
    Deletes old image files and database rows older than 7 days,
    except those that resulted in punishments (bot_replied = 1 or 2).
    """
    conn = sqlite3.connect('monitor.db')
    c = conn.cursor()
    
    # Fetch old logs that can be safely deleted
    c.execute("""
        SELECT attachment_url, target_attachment_url 
        FROM logs 
        WHERE created_at < DATETIME('now', '-7 days') 
          AND bot_replied NOT IN (1, 2)
    """)
    rows = c.fetchall()

    if rows:
        print(f"{len(rows)}件の古い画像ファイルを物理削除、実行中だよ")
        for att_url, t_att_url in rows:
            for p in [att_url, t_att_url]:
                if p and isinstance(p, str) and os.path.exists(p):
                    try:
                        os.remove(p)
                    except:
                        pass

    # Delete old DB rows
    c.execute("""
        DELETE FROM logs 
        WHERE created_at < DATETIME('now', '-7 days') 
          AND bot_replied NOT IN (1, 2)
    """)
    
    if c.rowcount > 0:
        print(f" {c.rowcount}件の古い記録を消去したよ。ストレージがすっきりしたね。")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    """
    Main loop:
    - Sync human reviews
    - Run batch processing every API_BATCH_INTERVAL seconds
    - Generate hourly report
    - Cleanup old data
    """
    print("……監シーシャ、全機能・超節約モードで待機中だよ。")
    last_api_run = 0

    while True: 
        try:
            sync_human_reviews()
            
            current_time = time.time()

            # Run heavy batch tasks only at defined intervals
            if current_time - last_api_run > API_BATCH_INTERVAL:
                process_logs_large_batch()
                generate_hourly_report()
                cleanup_db()
                last_api_run = current_time
                print(f"[{time.strftime('%H:%M:%S')}] 定期バッチ・お掃除完了したよ。")
                
        except Exception as e:
            # Catch any unexpected loop-level errors
            print(f"ループ内エラーが発生したみたい: {e}")
        
        time.sleep(POLLING_INTERVAL)
