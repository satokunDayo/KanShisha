# 監シーシャ (KanShisha)
AI-Human Hybrid Discord Moderation System

---

## DESCRIPTION / 概要  

&nbsp;&nbsp;This project was developed as a technical solution to the complex challenges of large-scale community management, specifically inspired by observing real-world governance issues in major gaming Discord servers. The core concept is a "Hybrid Symbiosis of AI Efficiency and Human Ethical Oversight."  
While the AI (Gemini 2.5 Flash-Lite) is trained to detect early signs of inappropriate behavior and toxicity, it serves exclusively as a "Advisor." We believe that final judgment—interpreting subtle nuances and preserving a community's unique culture—must remain in the hands of responsible human administrators.  
This tool is designed to minimize administrative burnout and prevent the centralization of power (moderator overreach), ensuring a sustainable environment where users enjoy "balanced freedom" under intelligent supervision.  

&nbsp;&nbsp;本プロジェクトは、大規模なコミュニティ運営におけるガバナンスの課題を解決するために開発されました。特に、大手ゲームの公式コミュニティで発生し得る「モデレーターの権限逸脱」や「運営コストの増大」という実課題に対する、技術的な回答です。  
最大のコンセプトは、「AIによる効率化」と「人間による倫理的判断」のハイブリッド（共生）です。AI（Gemini 2.5 Flash-Lite）は不適切な兆候を即座に検知する強力な「提案者」として機能しますが、最終的な審判——文脈の機微やコミュニティ独自の文化を汲み取った意思決定——は、常に人間（管理者）が行うべきであるという設計思想に基づいています。  
管理者が過度な業務負荷で疲弊することなく、常に余裕を持ってコミュニティを見守り、権限の固定化や暴走をシステム的に防ぎつつ、「質の高い自由」をユーザーに提供するためのツールです。  

---

## AI Collaboration Note / AIとの共作について

As I continued building my skills in Python and CSS, I collaborated with AI (Gemini 3 Flash) as a technical partner.  
This ongoing dialogue—covering architecture design, coding support, and UI debugging—allowed me to progress efficiently while strengthening my grasp of the underlying technologies.

Python と CSS の習得を進める中で、AI（Gemini 3 Flash）を技術的パートナーとして活用しました。  
アーキテクチャ設計、コーディング支援、UI デバッグにわたる継続的な対話を通じて、効率的に開発を進めると同時に、基盤となる技術への理解を深めることができました。

---

## Features / 主な機能

* **Observer**: 
    Constant log collection via discord.py.  
    discord.py による常時ログ収集  

* **BatchProcessor**:
    Cost‑optimized batch analysis using Gemini API.  
    The execution interval is fully configurable via API_BATCH_INTERVAL, POLLING_INTERVAL, and related parameters.  
    Gemini API を用いたコスト最適化バッチ解析。実行間隔は自由に調整可能  

* **Dashboard**:  
    Dark-theme UI built with Streamlit to reduce eye strain.   
    Streamlit によるダークテーマUI  

* **AI + Vision Analysis / AI + Vision 解析**:  
    Detects not only text toxicity but also NSFW/inappropriate images.   
    テキストの攻撃性と画像の不適切判定を同時に実施

* **Final Human Execution / 人間による最終執行**:  
    Admins review AI-scored logs. Sanctions are only sent when an admin confirms the **Toxic (NG)** status.  
    管理者が判定を確定させた瞬間のみ、Botが制裁を執行  

* **Storage Management / ストレージ管理**:  
    Automatically deletes old logs and images after 7 days to save space.   
    7日が経過した不要なデータを物理削除するお掃除機能  

* **Eye-Friendly UI / 視認性特化UI**:  
    A custom grey-and-white theme designed for long-term monitoring.   
    長時間の監視でも目が疲れにくい配色設計  

* **Direct Navigation via Deep Linking/Discord.pyの機能**:  
"The dashboard utilizes Discord's deep linking architecture (including @me routing for DMs) to provide moderators with instant, one-click access to the exact message context, minimizing response time."  
Discordのディープリンク構造（DM用の @me ルーティングを含む）を利用しており、モデレーターがワンクリックで正確な文脈にアクセスできるようになり、対応時間を最小限に抑えています。  

* **Direct Inquiries & Appeals [NEW] / 目安箱機能**:  
Captures DMs, mentions, and replies sent directly to the bot, bypassing heavy AI processing to send user inquiries directly to the admin dashboard.  
Bot宛てのDMやメンション、返信を検知し、重いAI処理をスキップして直接管理者のダッシュボードへ届ける新機能


---

## Structure / ディレクトリ構造  

```text
.
├── attachments/        # Storage for intercepted images (Auto-generated)
├── BatchProcessor.py  # AI Analysis & Database Maintenance
├── Dashboard.py       # Web UI for Administrators (Streamlit)
├── DiscordObserver.py # Bot for log collection
├── .env example       # Template for API keys
├── .gitignore         # Files to ignore for GitHub
└── requirements.txt   # List of required packages
```

---

## Getting Started / 導入方法

### 1. Installation / インストール

```bash
git clone https://github.com/satokunDayo/KanShisha.git
cd KanShisha
pip install -r requirements.txt
```

### 2. Configuration / 環境設定

Rename `.env example` to `.env` and fill in your Discord Bot Token and Gemini API Key.  
`.env example` を `.env` にリネームし、各キーを入力してください。

### 3. Launch / 起動方法

Open three terminals and run them in the following order:  
3つのターミナルを開き、以下の順番で実行してください。

1) **Terminal 1 (Required)**: `python DiscordObserver.py`
↓
2) **Terminal 2**: `python BatchProcessor.py`
↓
3) **Terminal 3**: `streamlit run Dashboard.py`

---

## Requirements

Python 3.10+
discord.py / google-genai / streamlit / pandas / pillow / python-dotenv

---

## Disclaimer / 免責事項

****
This tool is intended to assist community management and is NOT intended to exclude or discriminate against any race, creed, gender identity, etc.  
It should be used to suppress personal moderator overreach through the combination of objective AI data and rational human judgment.  

本ツールはコミュニティ運営の補助を目的としており、特定の人種、信条、ジェンダーアイデンティティ等を排斥する意図はありません。  
AIの客観的なデータ提示と、人間の理性的判断を組み合わせることで、モデレーター個人の主観による暴走を抑制し、健全な議論の場を守るために利用してください。  
