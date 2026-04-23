# 🔬 AutoResearch AI

**Intelligent Research Automation Platform** — discover papers, generate AI summaries, detect research gaps, track opportunities, and receive automated alerts — all orchestrated by **n8n** visual workflows.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red?logo=streamlit)](https://streamlit.io)
[![HuggingFace](https://img.shields.io/badge/AI-HuggingFace-yellow?logo=huggingface)](https://huggingface.co)
[![n8n](https://img.shields.io/badge/Automation-n8n-orange?logo=n8n)](https://n8n.io)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **Paper Discovery** | Search arXiv by keyword, date, relevance — save to personal library |
| 🧠 **AI Summarization** | BART-large-CNN abstractive summaries for each paper |
| 🔑 **Keyword Extraction** | LLM-powered keyword/concept extraction |
| 📈 **Trend Analysis** | Cross-paper keyword trends + AI narrative |
| 🔭 **Research Gap Detection** | Mistral-7B identifies underexplored research areas |
| 🎯 **Opportunity Tracker** | Kanban pipeline for professors, labs, internships |
| ✉️ **Outreach Emails** | AI-generated personalized academic emails |
| 🔔 **Alert System** | Daily/weekly paper alerts via Email or Telegram |
| 🤖 **n8n Automation** | 5 visual workflows — schedule, webhook, parallel, conditional |
| ⏰ **Python Scheduler** | Fallback built-in scheduler — no Docker, no cron |
| 🖥️ **CLI Tool** | Full-featured terminal interface |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A free [HuggingFace account](https://huggingface.co) + API token
- Node.js 18+ *(optional — for n8n workflow automation)*

### 1. Clone & Install

```bash
git clone <repo-url>
cd autoresearch-ai

# Create virtual environment
python -m venv venv

# Activate — Windows:
venv\Scripts\activate
# Activate — Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Windows:
copy .env.example .env

# Linux/Mac:
cp .env.example .env
```

Open `.env` and fill in:

```env
# Required — get free token at https://huggingface.co/settings/tokens
HUGGINGFACE_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional — for email alerts
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password   # Gmail: use App Password

# Optional — for Telegram alerts
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional — n8n (defaults to localhost:5678)
N8N_BASE_URL=http://localhost:5678
```

### 3. Start Services

**Windows (one click):**
```bat
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh && ./start.sh
```

**Or manually (3 terminals):**
```bash
# Terminal 1 — FastAPI backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Streamlit UI
streamlit run app.py

# Terminal 3 — n8n (optional but recommended)
n8n start
```

### 4. Open the App

| Service | URL |
|---------|-----|
| 🖥️ Streamlit UI | http://localhost:8501 |
| 📚 API Docs (Swagger) | http://localhost:8000/docs |
| 📄 API Docs (ReDoc) | http://localhost:8000/redoc |
| 🤖 n8n Editor | http://localhost:5678 |

---

## 🤖 AI Engine — HuggingFace

AutoResearch AI uses the **HuggingFace Inference API** as its sole AI engine:

| Task | Model |
|------|-------|
| Paper summarization | `facebook/bart-large-cnn` |
| Gap detection, trends, outreach email | `mistralai/Mistral-7B-Instruct-v0.3` |
| Keyword extraction | Mistral-7B (LLM) + TF-IDF fallback |

All AI features include **graceful extractive/template fallbacks** — the platform remains fully functional even if the HF API is rate-limited.

> **Free tier:** ~1,000 inference API calls/day. Upgrade to HF Pro for higher limits.

---

## 🔁 n8n Workflow Automation

n8n provides a **visual workflow editor** that orchestrates all scheduled and event-driven automation. Import any workflow from `n8n/workflows/` and activate it in one click.

### Setup

```bash
# Install once (requires Node.js 18+)
npm install -g n8n

# Start n8n — opens at http://localhost:5678
n8n start

# Or without global install
npx n8n start
```

### 5 Production Workflows

| # | Workflow | Trigger | Description |
|---|----------|---------|-------------|
| 01 | **Daily Paper Alert** | Every day 08:00 | Fetches all active topics in parallel → AI-summarizes → rich HTML email + Telegram |
| 02 | **Weekly Research Digest** | Monday 09:00 | Stats + trends (parallel fetch) → merged digest → email + Telegram summary |
| 03 | **Multi-Topic Monitor** | Every 1 hour | Smart monitor — fires Telegram only if **≥3 new papers** appear in any topic |
| 04 | **Research Gap Webhook** | HTTP POST | On-demand gap analysis → JSON response to caller + Telegram report |
| 05 | **Outreach Pipeline** | Tuesday 10:00 | Loops un-contacted opps → AI email → SMTP send → mark contacted → 2s delay |

### Import a Workflow

1. Start n8n → go to **http://localhost:5678**
2. **Workflows → Import from file** → select any `.json` from `n8n/workflows/`
3. Add credentials: **SMTP** (Settings → Credentials) and **Telegram API**
4. Click the **Active** toggle — done

### n8n-Optimised API Endpoints

These endpoints are built specifically for n8n consumption:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/n8n/topics` | All distinct topics as array (use with Split node) |
| `POST` | `/api/n8n/bulk-fetch` | Fetch papers for multiple topics in one call |
| `GET` | `/api/n8n/summary-stats` | Combined stats for digest header (one round-trip) |
| `POST` | `/api/n8n/batch-summarize` | AI-summarize up to N papers in one call |
| `POST` | `/webhook/gap-analysis` | Trigger AI gap analysis (called by WF-04) |
| `POST` | `/webhook/n8n-event` | Log n8n execution events into API logs |

### Trigger Gap Analysis via Webhook (WF-04)

```bash
# Call the n8n webhook URL after WF-04 is active and deployed
curl -X POST http://localhost:5678/webhook/gap-analysis \
     -H "Content-Type: application/json" \
     -d '{"topic": "federated learning privacy", "max_papers": 15}'

# Or call the FastAPI endpoint directly
curl -X POST http://localhost:8000/webhook/gap-analysis \
     -H "Content-Type: application/json" \
     -d '{"topic": "federated learning privacy"}'
```

---

## ⚙️ CLI Usage

```bash
# Fetch papers and save to DB
python cli.py fetch --query "graph neural networks" --max 30 --summarize

# Summarize all un-summarized papers
python cli.py summarize

# Show keyword trends
python cli.py trends --topic "deep learning"

# Detect research gaps
python cli.py gaps --topic "federated learning privacy"

# Show DB statistics
python cli.py stats

# Trigger an alert immediately
python cli.py alert --id 1
```

---

## ⏰ Python Scheduler (n8n alternative)

If you prefer not to run n8n, the built-in Python scheduler handles all automation:

```bash
# Start scheduler (keep this running in a separate terminal)
python services/scheduler.py

# Windows background process
start /min "Scheduler" python services/scheduler.py

# Linux background (nohup)
nohup python services/scheduler.py > scheduler.log 2>&1 &
```

Alerts configured in the UI are automatically picked up by the scheduler.

---

## 🏗️ Architecture

```
autoresearch-ai/
├── app.py                       # Streamlit entry point
├── backend/
│   ├── main.py                  # FastAPI app + all routes (incl. n8n endpoints)
│   └── database.py              # SQLAlchemy ORM models
├── services/
│   ├── ai_service.py            # HuggingFace AI engine (BART + Mistral-7B)
│   ├── arxiv_service.py         # arXiv paper fetching
│   ├── notification_service.py  # Email (SMTP) + Telegram Bot API
│   └── scheduler.py             # Built-in Python scheduler (n8n fallback)
├── pages/                       # Streamlit page modules
│   ├── dashboard.py
│   ├── discovery.py
│   ├── insights.py
│   ├── opportunities.py
│   ├── alerts.py                # Includes full n8n integration tab
│   └── settings.py
├── n8n/
│   └── workflows/               # Importable n8n workflow JSON files
│       ├── 01_daily_paper_alert.json
│       ├── 02_weekly_digest.json
│       ├── 03_multi_topic_monitor.json
│       ├── 04_research_gap_webhook.json
│       └── 05_outreach_pipeline.json
├── utils/
│   └── helpers.py               # API client + formatting helpers
├── cli.py                       # Command-line interface
├── start.bat                    # Windows one-click startup
├── start.sh                     # Linux/Mac one-click startup
├── Procfile                     # Heroku/Railway/Render deployment
├── requirements.txt
├── .env.example
└── autoresearch.db              # SQLite database (auto-created)
```

### API Route Groups

| Tag | Routes | Purpose |
|-----|--------|---------|
| `System` | `/health` | Liveness probe |
| `Papers` | `/api/papers/*` | Search, list, summarize, bookmark |
| `Insights` | `/api/insights/*` | Trends, research gaps |
| `Opportunities` | `/api/opportunities/*` | CRUD + email generation |
| `Alerts` | `/api/alerts/*` | CRUD + manual trigger |
| `n8n` | `/api/n8n/*` | Batch/bulk endpoints optimised for n8n |
| `Webhooks` | `/webhook/*` | n8n webhook receivers |

---

## 🌐 Cloud Deployment

### Render / Railway / Heroku

1. Push to GitHub
2. Set environment variables in the platform dashboard (copy from `.env`)
3. The `Procfile` declares the `api` and `web` processes automatically

```
api: uvicorn backend.main:app --host 0.0.0.0 --port 8000
web: streamlit run app.py --server.port $PORT --server.headless true
```

### Fly.io

```bash
fly launch
fly secrets set HUGGINGFACE_API_TOKEN=hf_xxx SMTP_USER=your@email.com ...
fly deploy
```

### n8n in Production

For cloud n8n, use [n8n Cloud](https://n8n.io/cloud) or self-host on Railway:

```bash
# Railway deployment
railway up --service n8n
```

Point n8n's HTTP Request nodes to your deployed API URL instead of `localhost:8000`.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
