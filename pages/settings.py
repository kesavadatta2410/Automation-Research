"""
pages/settings.py — Application Configuration
"""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def render():
    st.markdown("""
    <div class="page-header">
      <h1>⚙️ Settings</h1>
      <p>Configure AI models, notification channels, and application preferences.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🤖 AI Config", "📧 Notifications", "🗄️ Database", "📖 Docs"])

    # ── Tab 1: AI Config ──────────────────────────────────────────────────────
    with tab1:
        st.markdown("#### 🤗 HuggingFace Inference API")
        st.markdown(
            '<div class="ar-alert info">AutoResearch AI uses the HuggingFace Inference API '
            'as its AI engine. You need a free HuggingFace account to obtain a token.</div>',
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        hf_token = c1.text_input(
            "HF API Token",
            value=os.getenv("HUGGINGFACE_API_TOKEN", ""),
            type="password",
            help="Get your free token at https://huggingface.co/settings/tokens",
        )
        c2.markdown(
            '<br><small style="color:#888;">Free tier supports ~1000 API calls/day. '
            'Upgrade to PRO for higher limits.</small>',
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("#### 🧠 Model Selection")
        c1, c2 = st.columns(2)
        summarize_model = c1.selectbox(
            "Summarization Model",
            ["facebook/bart-large-cnn", "facebook/bart-large-xsum", "sshleifer/distilbart-cnn-12-6"],
            index=0,
            help="Used for abstractive paper summaries (BART family recommended).",
        )
        chat_model = c2.selectbox(
            "Reasoning / Chat Model",
            [
                "mistralai/Mistral-7B-Instruct-v0.3",
                "google/flan-t5-xxl",
                "HuggingFaceH4/zephyr-7b-beta",
            ],
            index=0,
            help="Used for keyword extraction, gap detection, and outreach email generation.",
        )

        st.markdown(
            f'<div class="ar-alert info">'
            f'<b>Active models:</b><br>'
            f'• Summarize: <code>{os.getenv("HF_MODEL_SUMMARIZE", summarize_model)}</code><br>'
            f'• Chat/Reason: <code>{os.getenv("HF_MODEL_CHAT", chat_model)}</code>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if st.button("🔌 Test HuggingFace Connection"):
            token = hf_token or os.getenv("HUGGINGFACE_API_TOKEN", "")
            if not token:
                st.error("No API token set. Add HUGGINGFACE_API_TOKEN to your .env file.")
            else:
                import requests as req
                with st.spinner("Testing connection..."):
                    try:
                        r = req.get(
                            "https://huggingface.co/api/whoami-v2",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=8,
                        )
                        if r.status_code == 200:
                            info = r.json()
                            st.success(
                                f"✅ Connected! Logged in as: **{info.get('name', 'unknown')}** "
                                f"(type: {info.get('type', 'user')})"
                            )
                        else:
                            st.error(f"Authentication failed: {r.status_code} — check your token.")
                    except Exception as e:
                        st.error(f"Connection error: {e}")

        st.markdown("---")
        st.markdown("#### 📌 How to get a HuggingFace Token")
        st.markdown("""
        1. Go to **[huggingface.co](https://huggingface.co)** → Sign up (free)
        2. Navigate to **Settings → Access Tokens**
        3. Click **New token** → select `read` role → copy the token
        4. Paste it into `HUGGINGFACE_API_TOKEN` in your `.env` file
        5. Restart the API backend
        """)
        st.link_button("🔗 Get HF Token", "https://huggingface.co/settings/tokens",
                       use_container_width=False)

    # ── Tab 2: Notifications ──────────────────────────────────────────────────
    with tab2:
        st.markdown("#### 📧 Email (SMTP)")
        c1, c2 = st.columns(2)
        smtp_host = c1.text_input("SMTP Host", value=os.getenv("SMTP_HOST", "smtp.gmail.com"))
        smtp_port = c2.text_input("SMTP Port", value=os.getenv("SMTP_PORT", "587"))
        smtp_user = c1.text_input("SMTP User", value=os.getenv("SMTP_USER", ""))
        smtp_pass = c2.text_input(
            "SMTP Password", value="", type="password",
            placeholder="Gmail: use an App Password",
        )

        if st.button("📧 Test Email"):
            from services.notification_service import send_email
            ok = send_email(
                to=smtp_user or "test@example.com",
                subject="AutoResearch AI — Test Email",
                body_html=(
                    "<h2>✅ Email working!</h2>"
                    "<p>AutoResearch AI email is configured correctly.</p>"
                ),
            )
            st.success("Test email sent!") if ok else st.error(
                "Failed. Check SMTP credentials in .env"
            )

        st.markdown("""
        **Gmail setup:**
        1. Enable 2-Step Verification on your Google account
        2. Go to **Security → App Passwords** → create one for "Mail"
        3. Use that 16-character password as `SMTP_PASSWORD`
        """)

        st.markdown("---")
        st.markdown("#### 📱 Telegram")
        c1, c2 = st.columns(2)
        tg_token   = c1.text_input("Bot Token",   value=os.getenv("TELEGRAM_BOT_TOKEN", ""),
                                    type="password")
        tg_chat_id = c2.text_input("Chat ID",     value=os.getenv("TELEGRAM_CHAT_ID", ""))

        if st.button("📱 Test Telegram"):
            from services.notification_service import send_telegram
            ok = send_telegram("🔬 *AutoResearch AI* — Test message! Bot is connected ✅")
            st.success("Telegram message sent!") if ok else st.error(
                "Failed. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
            )

        st.markdown("""
        **How to get Bot Token:**
        1. Open Telegram → search `@BotFather`
        2. `/newbot` → follow instructions → copy the token

        **How to get Chat ID:**
        1. Send a message to your bot
        2. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
        3. Find `chat.id` in the response
        """)

    # ── Tab 3: Database ───────────────────────────────────────────────────────
    with tab3:
        st.markdown("#### 🗄️ Database Info")
        db_url = os.getenv("DATABASE_URL", "sqlite:///./autoresearch.db")
        st.code(db_url)

        db_path = Path("autoresearch.db")
        if db_path.exists():
            size_kb = db_path.stat().st_size / 1024
            st.metric("DB File Size", f"{size_kb:.1f} KB")

        if st.button("🔄 Re-initialize Database"):
            from backend.database import init_db
            init_db()
            st.success("Database initialized ✅")

        st.markdown("---")
        st.markdown("#### Export Data")
        try:
            from utils.helpers import APIClient
            import pandas as pd

            api    = APIClient()
            data   = api.list_papers(limit=200)
            papers = data.get("papers", [])
            if papers:
                rows = [
                    {
                        "id":        p["id"],
                        "title":     p["title"],
                        "authors":   ", ".join(p.get("authors", [])) if isinstance(p.get("authors"), list) else p.get("authors", ""),
                        "abstract":  p.get("abstract", ""),
                        "summary":   p.get("summary", ""),
                        "published": p.get("published", ""),
                        "url":       p.get("url", ""),
                        "topic":     p.get("topic", ""),
                    }
                    for p in papers
                ]
                csv = pd.DataFrame(rows).to_csv(index=False)
                st.download_button(
                    "⬇️ Export Papers (CSV)",
                    data=csv,
                    file_name="autoresearch_papers.csv",
                    mime="text/csv",
                )
        except Exception:
            st.info("Start the API backend to enable data export.")

    # ── Tab 4: Docs ───────────────────────────────────────────────────────────
    with tab4:
        st.markdown("#### 📖 Quick Start")
        st.code("""
# 1. Clone and setup
git clone <repo-url> && cd autoresearch-ai
python -m venv venv

# Windows
venv\\Scripts\\activate
# Linux / Mac
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env        # Windows
# OR: cp .env.example .env   # Linux/Mac
# Edit .env — add your HUGGINGFACE_API_TOKEN

# 4. Start everything (Windows)
start.bat

# 4. Start everything (Linux/Mac)
chmod +x start.sh && ./start.sh

# ── Or manually ──────────────────────────────────────────────────
# Terminal 1 — FastAPI backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Streamlit UI
streamlit run app.py
        """, language="bash")

        st.markdown("#### API Documentation")
        c1, c2 = st.columns(2)
        c1.link_button("📚 Swagger Docs",  "http://localhost:8000/docs",  use_container_width=True)
        c2.link_button("📄 ReDoc",         "http://localhost:8000/redoc", use_container_width=True)

        st.markdown("#### Tech Stack")
        st.markdown("""
        | Layer | Technology |
        |-------|-----------|
        | Frontend | Streamlit |
        | Backend API | FastAPI + Python |
        | AI Engine | HuggingFace Inference API (BART + Mistral-7B) |
        | Database | SQLite (dev) / PostgreSQL (prod) |
        | Data Source | arXiv API |
        | Notifications | SMTP Email + Telegram Bot API |
        | Scheduling | Python `schedule` library |
        | Deployment | Native scripts / Heroku / Railway / Render |
        """)
