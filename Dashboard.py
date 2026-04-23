import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Configure the Streamlit page:
# - Title
# - Wide layout for dashboard-style UI
# - Custom emoji icon
st.set_page_config(page_title="監シーシャ", layout="wide", page_icon="🚨🚨")

# Inject custom CSS to override Streamlit's default theme.
# This ensures:
# - White text on dark background
# - Styled notifications
# - Styled links
# - Larger message text for readability
st.markdown("""
<style>
    .stApp, .stApp p, .stApp span, .stApp div {
        color: #ffffff !important;
    }

    div[data-testid="stNotification"], div[role="alert"] {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #464b5d !important;
        border-radius: 8px;
    }
    
    div[data-testid="stNotification"] div, 
    div[data-testid="stNotification"] p, 
    div[data-testid="stNotification"] span,
    div[data-testid="stNotification"] svg {
        color: #ffffff !important;
        fill: #ffffff !important;
    }

    a, a * {
        color: #00d4ff !important;
        text-decoration: underline !important;
        font-weight: bold !important;
    }

    .big-message {
        font-size: 28px !important;
        font-weight: bold !important;
        color: #ffffff !important;
        margin: 20px 0;
        line-height: 1.4;
    }
</style>
""", unsafe_allow_html=True)

# Main title and description
st.title("監シーシャ")
st.caption("……このダッシュボードは、Discordのコミュニティを見守り、裁くためのものだよ。")

# Utility function to open a SQLite connection
def get_db():
    return sqlite3.connect('monitor.db')

conn = get_db()

# -----------------------------
# Sidebar: Recent AI-generated reports
# -----------------------------
st.sidebar.header("📑分析レポート")

try:
    # Fetch the 5 most recent reports
    rdf = pd.read_sql(
        "SELECT report_text, created_at FROM reports ORDER BY created_at DESC LIMIT 5",
        conn
    )

    if not rdf.empty:
        # Display each report inside an expander
        for i, r in rdf.iterrows():
            with st.sidebar.expander(f"📅 {r['created_at']}"):
                st.info(r['report_text'])
    else:
        st.sidebar.write("分析データはまだ届いていないよ。")

except:
    # If the table doesn't exist yet or DB is locked
    st.sidebar.write("レポートは準備中だよ")

# -----------------------------
# Main Section: Log Filtering UI
# -----------------------------
st.header("記録")

with st.container():
    # Text search for usernames
    u_search = st.text_input("ユーザー名で検索", placeholder="名前の一部を入れてね...")

    # Four-column layout for filters
    col_date1, col_date2, col_off, col_def = st.columns([2, 2, 1, 1])
    
    with col_date1:
        # Start date filter
        start_date = st.date_input("開始日", value=None)
    with col_date2:
        # End date filter
        end_date = st.date_input("終了日", value=None)
    with col_off:
        # Minimum offense score filter
        min_offense = st.number_input("Min Offense", 0, 10, 0)
    with col_def:
        # Minimum defense score filter
        min_rebuke = st.number_input("Min Defence", 0, 10, 0)

    # Checkbox to show only pending human review items
    show_only_pending = st.checkbox("未レビュー（pending）のみ表示")

# -----------------------------
# Build SQL query dynamically based on filters
# -----------------------------
query = "SELECT * FROM logs WHERE offensive_score >= ? AND rebuke_score >= ?"
params = [min_offense, min_rebuke]

# Add date filters if provided
if start_date:
    query += " AND created_at >= ?"
    params.append(f"{start_date} 00:00:00")

if end_date:
    query += " AND created_at <= ?"
    params.append(f"{end_date} 23:59:59")

# Username search (matches both sender and target)
if u_search:
    query += " AND (user_name LIKE ? OR target_user_name LIKE ?)"
    params.extend([f"%{u_search}%", f"%{u_search}%"])

# Only show pending items
if show_only_pending:
    query += " AND human_review_status = 'pending'"

# Sort newest first and limit to 100 rows for performance
query += " ORDER BY created_at DESC LIMIT 100"

# Execute query
df = pd.read_sql(query, conn, params=params)

# Manual refresh button
if st.button("🔄情報を更新（Refresh）"):
    st.rerun()

# Display number of results
st.markdown(f"**解析結果:** {len(df)} 件の記録を見つけたよ。")

# -----------------------------
# Display results
# -----------------------------
if df.empty:
    # Peaceful state: no toxic messages found
    st.success("……平和なものね。条件に合う記録は見当たらないよ。")

else:
    # Iterate through each log entry
    for i, row in df.iterrows():
        with st.container():
            st.markdown("---")

            # Three-column layout:
            # c1 = scores + timestamp
            # c2 = message context + images + summary
            # c3 = human review dropdown
            c1, c2, c3 = st.columns([1.5, 5, 2.5])
            
            # -----------------------------
            # Column 1: Scores + timestamp
            # -----------------------------
            with c1:
                st.metric("Offense", f"{row['offensive_score']}/10")
                st.metric("Defence", f"{row['rebuke_score']}/10")
                st.caption(f" {row['created_at']}")

            # -----------------------------
            # Column 2: Message content and context
            # -----------------------------
            with c2:
                st.markdown(f"**{row['user_name']}** ➔ **{row['target_user_name'] or 'Channel'}**")
                
                # Expander showing the replied-to message context
                with st.expander("文脈を表示（リプライ先）", expanded=True):

                    # Display target image if exists
                    t_img = row.get('target_attachment_url')
                    if pd.notna(t_img) and t_img:
                        st.image(t_img, use_container_width=True)

                        # Link to original target message
                        t_link = row.get('target_jump_url')
                        if pd.notna(t_link) and t_link:
                            st.markdown(f"**[この画像が貼られた投稿へ飛ぶ]({t_link})**")
                    
                    # Display target text if exists
                    t_txt = row.get('target_content')
                    if pd.notna(t_txt) and t_txt:
                        st.info(f"元のメッセージ: {t_txt}")

                # Main message content
                msg_content = row['content'] or '[画像のみ]'
                st.markdown(
                    f"<div class='big-message'>発言内容:  {msg_content}</div>",
                    unsafe_allow_html=True
                )
                
                # Display user image if exists
                u_img = row.get('attachment_url')
                if pd.notna(u_img) and u_img:
                    st.image(u_img, use_container_width=True)

                # If content is a direct image URL (GIF, PNG, etc.)
                elif pd.notna(row['content']) and str(row['content']).startswith('http'):
                    if any(x in str(row['content']).lower() for x in ['.gif', '.png', '.jpg', 'klipy', 'tenor']):
                        st.image(row['content'], use_container_width=True)

                # Link to the message on Discord
                st.write(f"[この発言をDiscordで確認]({row['jump_url']})")

                # AI summary
                st.caption(f"**AI要約:** {row['summary']}")

            # -----------------------------
            # Column 3: Human review dropdown
            # -----------------------------
            with c3:
                status = st.selectbox(
                    "判定確定",
                    ["pending", "Banter (OK)", "Toxic (NG)"],
                    index=["pending", "Banter (OK)", "Toxic (NG)"].index(row['human_review_status']),
                    key=f"status_{row['id']}"
                )
                
                # If the reviewer changes the status, update DB
                if status != row['human_review_status']:
                    conn.execute(
                        "UPDATE logs SET human_review_status = ? WHERE id = ?",
                        (status, row['id'])
                    )
                    conn.commit()

                    # Feedback to reviewer
                    if status == "Toxic (NG)":
                        st.warning("粛清対象に設定したよ。Botに警告させるね。")
                    else:
                        st.toast(f"判定を {status} に更新したよ。")

# Close DB connection
conn.close()
