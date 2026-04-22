"""
pages/settings.py — Application Configuration
"""
import streamlit as st
import os
from pathlib import Path
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
        st.markdown("#### Ollama (Local LLM)")
        c1, c2 = st.columns(2)
        ollama_url   = c1.text_input("Ollama URL",   value=os.getenv("OLLAMA_BASE_URL","http://localhost:11434"))
        ollama_model = c2.text_input("Ollama Model", value=os.getenv("OLLAMA_MODEL","llama3"))

        if st.button("🔌 Test Ollama Connection"):
            import requests
            try:
                r = requests.get(f"{ollama_url}/api/tags", timeout=3)
                if r.ok:
                    models = [m["name"] for m in r.json().get("models", [])]
                    st.success(f"✅ Connected! Models: {', '.join(models) or 'none pulled'}")
                else:
                    st.error(f"Error: {r.status_code}")
            except Exception as e:
                st.error(f"Cannot connect to Ollama: {e}")

        st.markdown("**Pull a Model:**")
        st.code("ollama pull llama3\nollama pull mistral\nollama pull phi3", language="bash")

        st.markdown("---")
        st.markdown("#### HuggingFace (Cloud Fallback)")
        hf_token = st.text_input("HF API Token", value=os.getenv("HUGGINGFACE_API_TOKEN",""),
                                  type="password")
        st.markdown('<small style="color:#888;">Used as fallback when Ollama is unavailable.</small>',
                    unsafe_allow_html=True)

    # ── Tab 2: Notifications ──────────────────────────────────────────────────
    with tab2:
        st.markdown("#### 📧 Email (SMTP)")
        c1, c2 = st.columns(2)
        smtp_host = c1.text_input("SMTP Host", value=os.getenv("SMTP_HOST","smtp.gmail.com"))
        smtp_port = c2.text_input("SMTP Port", value=os.getenv("SMTP_PORT","587"))
        smtp_user = c1.text_input("SMTP User", value=os.getenv("SMTP_USER",""))
        smtp_pass = c2.text_input("SMTP Password", value="", type="password",
                                   placeholder="App password (not account password)")

        if st.button("📧 Test Email"):
            from services.notification_service import send_email
            ok = send_email(
                to=smtp_user or "test@example.com",
                subject="AutoResearch AI — Test Email",
                body_html="<h2>✅ Email working!</h2><p>AutoResearch AI email is configured correctly.</p>",
            )
            if ok:
                st.success("Test email sent!")
            else:
                st.error("Failed. Check SMTP credentials in .env")

        st.markdown("---")
        st.markdown("#### 📱 Telegram")
        c1, c2 = st.columns(2)
        tg_token   = c1.text_input("Bot Token", value=os.getenv("TELEGRAM_BOT_TOKEN",""),
                                    type="password")
        tg_chat_id = c2.text_input("Chat ID",   value=os.getenv("TELEGRAM_CHAT_ID",""))

        if st.button("📱 Test Telegram"):
            from services.notification_service import send_telegram
            ok = send_telegram("🔬 *AutoResearch AI* — Test message! Bot is connected ✅")
            if ok:
                st.success("Telegram message sent!")
            else:
                st.error("Failed. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")

        st.markdown("""
        **How to get Bot Token:**
        1. Open Telegram → search `@BotFather`
        2. `/newbot` → follow instructions
        3. Copy the token

        **How to get Chat ID:**
        1. Send a message to your bot
        2. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
        3. Find `chat.id` in response
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
            api = APIClient()
            data = api.list_papers(limit=200)
            papers = data.get("papers", [])
            if papers:
                import pandas as pd, json
                rows = []
                for p in papers:
                    authors = p.get("authors",[])
                    rows.append({
                        "id": p["id"], "title": p["title"],
                        "authors": ", ".join(authors) if isinstance(authors,list) else authors,
                        "abstract": p.get("abstract",""),
                        "summary": p.get("summary",""),
                        "published": p.get("published",""),
                        "url": p.get("url",""),
                        "topic": p.get("topic",""),
                    })
                df = pd.DataFrame(rows)
                csv = df.to_csv(index=False)
                st.download_button(
                    "⬇️ Export Papers (CSV)",
                    data=csv,
                    file_name="autoresearch_papers.csv",
                    mime="text/csv",
                )
        except Exception:
            pass

    # ── Tab 4: Docs ───────────────────────────────────────────────────────────
    with tab4:
        st.markdown("#### 📖 Quick Start")
        st.code("""
# 1. Clone and setup
git clone <repo-url> && cd autoresearch-ai
python -m venv venv && source venv/bin/activate   # Linux/Mac
# OR: venv\\Scripts\\activate                      # Windows

# 2. Install deps
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Start FastAPI backend (terminal 1)
uvicorn backend.main:app --reload --port 8000

# 5. Start Streamlit (terminal 2)
streamlit run app.py

# 6. Optional: Start Ollama
ollama serve
ollama pull llama3
        """, language="bash")

        st.markdown("#### API Documentation")
        c1, c2 = st.columns(2)
        c1.link_button("📚 Swagger Docs", "http://localhost:8000/docs", use_container_width=True)
        c2.link_button("📄 ReDoc", "http://localhost:8000/redoc", use_container_width=True)

        st.markdown("#### Tech Stack")
        st.markdown("""
        | Layer | Technology |
        |-------|-----------|
        | Frontend | Streamlit |
        | Backend API | FastAPI + Python |
        | AI Engine | Ollama (llama3) + HuggingFace BART |
        | Automation | n8n workflows |
        | Database | SQLite (dev) / PostgreSQL (prod) |
        | Data Source | arXiv API |
        | Notifications | SMTP Email + Telegram |
        """)
