# 🔬 AutoResearch AI

> **Intelligent Research Automation Platform** — Discover papers, generate AI summaries, detect trends & gaps, and automate outreach.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **Paper Discovery** | Fetch latest papers from arXiv by keyword/topic |
| 🧠 **AI Summarization** | Auto-summarize papers using Ollama (llama3) or HuggingFace BART |
| 🔑 **Keyword Extraction** | Extract key concepts and themes from abstracts |
| 📈 **Trend Analysis** | Identify emerging research trends across paper collections |
| 🔭 **Research Gap Detection** | AI-powered identification of unexplored research directions |
| 🎯 **Opportunity Tracking** | Kanban pipeline for professors, labs, and internships |
| ✉️ **Email Generation** | Personalized outreach emails via AI |
| 🔔 **Alerts** | Daily/weekly paper alerts via Email and Telegram |
| 🤖 **n8n Automation** | Workflow templates for scheduled automation |
| 📊 **Dashboard** | Metrics, recent papers, and quick search |

---

## 🚀 Quick Start

### Option A — Local Development

```bash
# 1. Clone
git clone <repository-url>
cd autoresearch-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials (see Configuration section)

# 5. Start FastAPI backend (Terminal 1)
uvicorn backend.main:app --reload --port 8000

# 6. Start Streamlit UI (Terminal 2)
streamlit run app.py

# 7. (Optional) Start Ollama for local AI
ollama serve
ollama pull llama3
```

Open: http://localhost:8501

### Option B — Docker Compose (Recommended)

```bash
# Start all services (API + UI + Ollama + n8n + Scheduler)
docker compose up -d

# Pull Ollama model (first time only)
docker exec autoresearch_ollama ollama pull llama3

# View logs
docker compose logs -f api
```

Services:
- **UI**: http://localhost:8501
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **n8n**: http://localhost:5678 (admin / autoresearch2024)
- **Ollama**: http://localhost:11434

---

## ⚙️ Configuration


# Backend API URL
API_BASE_URL=http://localhost:8000
API Docs
http://localhost:8000/docs
n8n
http://localhost:5678

---

## 📡 API Reference

Full interactive docs: http://localhost:8000/docs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/papers/search` | Search arXiv, store results |
| GET | `/api/papers` | List saved papers |
| POST | `/api/papers/{id}/summarize` | AI-summarize a paper |
| PATCH | `/api/papers/{id}/bookmark` | Toggle bookmark |
| GET | `/api/insights/trends` | Keyword trend analysis |
| GET | `/api/insights/gaps` | Research gap detection |
| GET/POST | `/api/opportunities` | Manage research opportunities |
| POST | `/api/opportunities/{id}/generate-email` | Generate outreach email |
| GET/POST | `/api/alerts` | Manage notification alerts |
| POST | `/api/alerts/{id}/trigger` | Manually trigger alert |

---

## 🖥️ CLI Usage

```bash
# Fetch papers
python cli.py fetch --query "large language models" --max 30 --summarize

# Analyze trends
python cli.py trends --topic "deep learning"

# Detect research gaps
python cli.py gaps --topic "federated learning"

# Database stats
python cli.py stats

# Trigger alert manually
python cli.py alert --id 1

# Summarize all unsummarized papers
python cli.py summarize
```

---

## 🤖 n8n Automation Setup

1. **Install n8n:**
   ```bash
   npm install -g n8n   # or use Docker
   n8n start
   ```

2. **Import workflows:**
   - Open http://localhost:5678
   - Workflows → Import → Upload files from `n8n/workflows/`

3. **Configure credentials:**
   - Add SMTP credential
   - Add Telegram Bot credential

4. **Activate workflows**

Included templates:
- `daily_alerts.json` — Runs at 8 AM, fetches new papers, sends email + Telegram
- `weekly_report.json` — Runs Monday 9 AM, sends research digest

**No n8n?** Use the built-in Python scheduler:
```bash
python services/scheduler.py
```

---

## 🏗️ Project Architecture

```
autoresearch-ai/
├── app.py                        # Streamlit main (routing + global CSS)
├── cli.py                        # Command-line interface
├── docker-compose.yml            # Full-stack deployment
├── Dockerfile
├── requirements.txt
├── .env.example
│
├── backend/
│   ├── main.py                   # FastAPI app + all routes
│   └── database.py               # SQLAlchemy models + session
│
├── services/
│   ├── arxiv_service.py          # arXiv API client
│   ├── ai_service.py             # Ollama + HuggingFace AI layer
│   ├── notification_service.py   # SMTP + Telegram
│   └── scheduler.py              # Python-based alert scheduler
│
├── pages/
│   ├── dashboard.py              # Home dashboard
│   ├── discovery.py              # Paper search + library
│   ├── insights.py               # Trends + gaps + concept map
│   ├── opportunities.py          # Outreach pipeline
│   ├── alerts.py                 # Alert config + n8n
│   └── settings.py               # App configuration
│
├── utils/
│   └── helpers.py                # APIClient + formatters
│
└── n8n/workflows/
    ├── daily_alerts.json         # n8n daily paper alert
    └── weekly_report.json        # n8n weekly digest
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit 1.32 |
| Backend | FastAPI + Python 3.11 |
| AI Engine | Ollama (llama3) + HuggingFace BART |
| Automation | n8n + Python schedule |
| Database | SQLite (dev) · PostgreSQL (prod) |
| Data Source | arXiv API |
| Notifications | SMTP Email · Telegram Bot API |
| Deployment | Docker Compose · Streamlit Cloud · Render |

---

## 🚢 Production Deployment

### Streamlit Cloud (UI)
1. Push to GitHub
2. Connect at share.streamlit.io
3. Set secrets in Streamlit Cloud dashboard

### Render / Railway (API)
```bash
# Build command
pip install -r requirements.txt

# Start command
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### PostgreSQL (Production DB)
```env
DATABASE_URL=postgresql://user:password@host:5432/autoresearch
```

---

## 📄 License

MIT License — see LICENSE file.

---

*Built with ❤️ for researchers, by researchers.*
