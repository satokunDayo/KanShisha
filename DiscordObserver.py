import discord
import sqlite3
import os
from discord.ext import tasks
from dotenv import load_dotenv

# Load environment variables from .env (Discord BOT TOKEN)
load_dotenv()
TOKEN = os.getenv('TOKEN')  

# initialize database and create tables if they don't exist
def init_db():
    """
    Initialize the SQLite database.
    This ensures the table schema is always up-to-date, including new columns 
    such as target_jump_url.
    """
    conn = sqlite3.connect('monitor.db')
    c = conn.cursor()

    # Create the main logs table if it does not exist.
    # This table stores:
    # - The message author
    # - The replied-to message (target)
    # - Message content, attachments, jump URLs
    # - AI analysis fields (offensive_score, rebuke_score, summary, etc.)
    # - Flags for bot actions and human review
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (id INTEGER PRIMARY KEY, 
                  user_id TEXT, user_name TEXT, 
                  target_user_id TEXT, target_user_name TEXT,
                  target_content TEXT, target_attachment_url TEXT,
                  target_jump_url TEXT, 
                  content TEXT, jump_url TEXT, attachment_url TEXT,
                  offensive_score INTEGER DEFAULT 0, 
                  rebuke_score INTEGER DEFAULT 0,
                  summary TEXT, vision_result TEXT, 
                  processed INTEGER DEFAULT 0,
                  bot_replied INTEGER DEFAULT 0,
                  human_review_status TEXT DEFAULT 'pending',
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    # Simple table for storing generated reports
    c.execute('''CREATE TABLE IF NOT EXISTS reports 
                 (id INTEGER PRIMARY KEY, 
                  report_text TEXT, 
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()
    conn.close()


class GuardianBot(discord.Client):
    """
    Custom Discord client that:
    - Records reply-chain messages into a database
    - Saves attachments locally
    - Periodically checks for messages requiring bot intervention
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        """
        Called once when the bot is preparing to start.
        Good place to initialize DB and start background tasks.
        """
        init_db()
        print("……準備が整ったよ。行こうか。")  # Startup message
        self.check_punishment.start()  # Start periodic task

    async def on_ready(self):
        """Triggered when the bot successfully logs in."""
        print(f"[{self.user}] としてログイン成功したよ。これからよろしくね。")

    async def on_message(self, message):
        """
        Triggered whenever a message is sent in a channel the bot can see.
        This bot only records messages that are replies (message.reference exists).
        """
        # Ignore bot's own messages and non-replies
        if message.author == self.user or not message.reference:
            return

        author_name = str(message.author.name)

        # Save attachment from the new message (if any)
        local_path = None
        if message.attachments:
            os.makedirs('attachments', exist_ok=True)
            attachment = message.attachments[0]

            # Extract file extension safely
            ext = attachment.filename.split('.')[-1] if '.' in attachment.filename else 'png'
            local_path = f"attachments/{message.id}.{ext}"

            # Save the file locally
            await attachment.save(local_path)

        # Prepare variables for the replied-to message (target)
        target_name, target_id = None, None
        target_content, target_local_path, target_jump_url = None, None, None

        try:
            # Fetch the message being replied to
            ref_msg = await message.channel.fetch_message(message.reference.message_id)

            target_name = str(ref_msg.author.name)
            target_id = str(ref_msg.author.id)
            target_content = ref_msg.content
            target_jump_url = ref_msg.jump_url  # URL to jump directly to the target message

            # Save attachment from the target message (if any)
            if ref_msg.attachments:
                os.makedirs('attachments', exist_ok=True)
                t_attach = ref_msg.attachments[0]
                t_ext = t_attach.filename.split('.')[-1] if '.' in t_attach.filename else 'png'
                target_local_path = f"attachments/target_{ref_msg.id}.{t_ext}"
                await t_attach.save(target_local_path)

        except Exception:
            # If the referenced message cannot be fetched (deleted, missing perms, etc.)
            pass

        # Insert the collected data into the database
        conn = sqlite3.connect('monitor.db')
        c = conn.cursor()
        c.execute("""
            INSERT INTO logs (
                user_id, user_name, 
                target_user_id, target_user_name, 
                target_content, target_attachment_url, target_jump_url, 
                content, jump_url, attachment_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(message.author.id), author_name,
            target_id, target_name,
            target_content, target_local_path, target_jump_url,
            message.content, message.jump_url, local_path
        ))
        conn.commit()
        conn.close()

        # Console output for debugging/logging
        display_content = message.content if message.content else "[画像/GIFのみ]"
        print(f"記録したよ。 {author_name} → {target_name} : {display_content}")

    @tasks.loop(seconds=15)
    async def check_punishment(self):
        """
        Periodic task that checks for messages requiring bot intervention.
        bot_replied values:
            1 → warn the user on their own message
            2 → warn the user on the target message
           -1 → already processed
           -2 → failed to process
        """
        try:
            conn = sqlite3.connect('monitor.db')
            c = conn.cursor()

            # Fetch messages that require bot action
            c.execute("SELECT id, jump_url, target_jump_url, bot_replied FROM logs WHERE bot_replied IN (1, 2)")
            targets = c.fetchall()

            if targets:
                print(f"[{self.user}] 粛清対象を {len(targets)} 件検知。botに警告させるね。")

            for row_id, jump_url, target_jump_url, r_type in targets:
                try:
                    # Determine which message to reply to
                    final_url = target_jump_url if (r_type == 2 and target_jump_url) else jump_url

                    # jump_url format: https://discord.com/channels/<guild>/<channel>/<message>
                    parts = final_url.split('/')
                    channel_id = int(parts[-2])
                    msg_id = int(parts[-1])

                    # Fetch the channel and message
                    channel = self.get_channel(channel_id) or await self.fetch_channel(channel_id)
                    msg = await channel.fetch_message(msg_id)

                    # Send appropriate warning message
                    if r_type == 1:
                        await msg.reply("……やめておいたほうがいいよ。これ以上は、君が困る結果になるだろうから。")
                    elif r_type == 2:
                        await msg.reply("…ねえ、覚えておいて。私たちの視線は、いつだってここにあること。")

                    # Mark as processed
                    c.execute("UPDATE logs SET bot_replied = -1 WHERE id = ?", (row_id,))
                    conn.commit()

                    print(f"執行完了。 ID:{row_id} の対象へ警告したよ。")

                except Exception as e:
                    # Mark as failed
                    c.execute("UPDATE logs SET bot_replied = -2 WHERE id = ?", (row_id,))
                    conn.commit()

            conn.close()

        except sqlite3.OperationalError:
            # DB locked or unavailable momentarily
            pass


# Enable message content intent (required for reading message text)
intents = discord.Intents.default()
intents.message_content = True

# Create and run the bot
client = GuardianBot(intents=intents)
client.run(TOKEN)
