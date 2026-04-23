"""
backend/main.py — AutoResearch AI · FastAPI application
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from backend.database import (
    Alert,
    Opportunity,
    OutreachEmail,
    Paper,
    ResearchGap,
    Trend,
    get_db,
    init_db,
    SessionLocal,
)
from services.arxiv_service import fetch_papers
from services.ai_service import (
    analyze_trends,
    detect_research_gaps,
    extract_keywords,
    generate_outreach_email,
    summarize_paper,
)
from services.notification_service import send_paper_alert, send_telegram_paper_alert

# ── Allowed origins (configure via CORS_ORIGINS env, comma-separated) ─────────
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
ALLOWED_ORIGINS: List[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise resources on startup; clean up on shutdown."""
    init_db()
    logger.info("AutoResearch AI API started ✓")
    yield
    logger.info("AutoResearch AI API shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AutoResearch AI",
    description=(
        "Intelligent Research Automation Platform — "
        "paper discovery, AI summarization, trend analysis, "
        "research gap detection, and outreach automation."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# ── Request Schemas ───────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    max_results: int = 20
    sort_by: str = "relevance"
    date_filter_days: Optional[int] = None
    auto_summarize: bool = False


class OutreachRequest(BaseModel):
    professor_name: str
    institution: str
    research_area: str
    your_background: str
    your_name: str


class OpportunityCreate(BaseModel):
    type: str
    name: str
    institution: str
    email: Optional[str] = None
    research_area: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None


class AlertCreate(BaseModel):
    topic: str
    channel: str       # email | telegram
    frequency: str     # daily | weekly


# ── n8n / Webhook Schemas ────────────────────────────────────────────────────

class BulkFetchRequest(BaseModel):
    topics: List[str]
    max_results: int = 10
    date_filter_days: Optional[int] = 1
    auto_summarize: bool = False


class BatchSummarizeRequest(BaseModel):
    paper_ids: List[str]
    limit: int = 5


class GapWebhookRequest(BaseModel):
    topic: str
    max_papers: int = 15


class N8nEventRequest(BaseModel):
    workflow: str
    event: str    # execution_started | execution_finished | error
    status: str   # success | error | running
    message: str = ""
    data: dict = {}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    """Liveness probe — returns 200 when API is running."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── Papers ────────────────────────────────────────────────────────────────────

@app.post("/api/papers/search", tags=["Papers"])
def search_papers(req: SearchRequest, db=Depends(get_db)):
    """Fetch papers from arXiv, persist new entries, optionally AI-summarize."""
    papers = fetch_papers(
        query=req.query,
        max_results=req.max_results,
        sort_by=req.sort_by,
        date_filter_days=req.date_filter_days,
    )

    saved = 0
    for p in papers:
        if db.query(Paper).filter(Paper.id == p["id"]).first():
            continue

        summary = ""
        keywords = "[]"
        if req.auto_summarize:
            try:
                summary = summarize_paper(p["title"], p["abstract"])
                kw_list = extract_keywords(f"{p['title']} {p['abstract']}")
                keywords = json.dumps(kw_list)
            except Exception as exc:
                logger.warning(f"Auto-summarize failed for {p['id']}: {exc}")

        db.add(
            Paper(
                id=p["id"],
                title=p["title"],
                authors=p["authors"],
                abstract=p["abstract"],
                summary=summary,
                keywords=keywords,
                categories=p.get("categories", ""),
                published=(
                    datetime.fromisoformat(p["published"])
                    if p.get("published")
                    else None
                ),
                url=p["url"],
                pdf_url=p.get("pdf_url", ""),
                topic=req.query,
            )
        )
        saved += 1

    db.commit()
    return {
        "message": f"Fetched {len(papers)} papers, saved {saved} new.",
        "papers": papers,
    }


@app.get("/api/papers", tags=["Papers"])
def list_papers(
    topic: Optional[str] = None,
    bookmarked: Optional[bool] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db=Depends(get_db),
):
    """List saved papers with optional filtering."""
    q = db.query(Paper)
    if topic:
        q = q.filter(Paper.topic.ilike(f"%{topic}%"))
    if bookmarked is not None:
        q = q.filter(Paper.is_bookmarked == bookmarked)
    total = q.count()
    papers = q.order_by(Paper.published.desc()).offset(offset).limit(limit).all()
    return {"total": total, "papers": [_paper_to_dict(p) for p in papers]}


@app.get("/api/papers/{paper_id}", tags=["Papers"])
def get_paper(paper_id: str, db=Depends(get_db)):
    """Retrieve a single paper by arXiv ID."""
    p = db.query(Paper).filter(Paper.id == paper_id).first()
    if not p:
        raise HTTPException(404, "Paper not found")
    return _paper_to_dict(p)


@app.post("/api/papers/{paper_id}/summarize", tags=["Papers"])
def summarize(paper_id: str, db=Depends(get_db)):
    """Generate AI summary + keywords for a stored paper."""
    p = db.query(Paper).filter(Paper.id == paper_id).first()
    if not p:
        raise HTTPException(404, "Paper not found")
    p.summary = summarize_paper(p.title, p.abstract)
    kw_list = extract_keywords(f"{p.title} {p.abstract}")
    p.keywords = json.dumps(kw_list)
    db.commit()
    return {"summary": p.summary, "keywords": kw_list}


@app.patch("/api/papers/{paper_id}/bookmark", tags=["Papers"])
def toggle_bookmark(paper_id: str, db=Depends(get_db)):
    """Toggle the bookmark flag on a paper."""
    p = db.query(Paper).filter(Paper.id == paper_id).first()
    if not p:
        raise HTTPException(404, "Paper not found")
    p.is_bookmarked = not p.is_bookmarked
    db.commit()
    return {"bookmarked": p.is_bookmarked}


# ── AI Insights ───────────────────────────────────────────────────────────────

@app.get("/api/insights/trends", tags=["Insights"])
def get_trends(
    topic: Optional[str] = None, limit: int = 30, db=Depends(get_db)
):
    """Analyze keyword trends across stored papers."""
    q = db.query(Paper)
    if topic:
        q = q.filter(Paper.topic.ilike(f"%{topic}%"))
    papers = q.order_by(Paper.published.desc()).limit(limit).all()
    return analyze_trends([_paper_to_dict(p) for p in papers])


@app.get("/api/insights/gaps", tags=["Insights"])
def get_gaps(topic: str, db=Depends(get_db)):
    """Detect research gaps for a topic from stored papers."""
    papers = (
        db.query(Paper)
        .filter(Paper.topic.ilike(f"%{topic}%"))
        .order_by(Paper.published.desc())
        .limit(15)
        .all()
    )
    gaps = detect_research_gaps([_paper_to_dict(p) for p in papers], topic)
    return {"topic": topic, "gaps": gaps}


# ── Opportunities ─────────────────────────────────────────────────────────────

@app.get("/api/opportunities", tags=["Opportunities"])
def list_opportunities(
    type: Optional[str] = None,
    contacted: Optional[bool] = None,
    db=Depends(get_db),
):
    q = db.query(Opportunity)
    if type:
        q = q.filter(Opportunity.type == type)
    if contacted is not None:
        q = q.filter(Opportunity.contacted == contacted)
    return [_opp_to_dict(o) for o in q.all()]


@app.post("/api/opportunities", tags=["Opportunities"])
def create_opportunity(data: OpportunityCreate, db=Depends(get_db)):
    opp = Opportunity(**data.model_dump())
    db.add(opp)
    db.commit()
    db.refresh(opp)
    return _opp_to_dict(opp)


@app.post("/api/opportunities/{opp_id}/generate-email", tags=["Opportunities"])
def gen_email(opp_id: int, req: OutreachRequest, db=Depends(get_db)):
    """Generate a personalized outreach email and persist it."""
    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(404, "Opportunity not found")

    result = generate_outreach_email(
        professor_name=req.professor_name,
        institution=req.institution,
        research_area=req.research_area,
        your_background=req.your_background,
        your_name=req.your_name,
    )
    db.add(
        OutreachEmail(
            opportunity_id=opp_id,
            subject=result["subject"],
            body=result["body"],
        )
    )
    db.commit()
    return result


@app.patch("/api/opportunities/{opp_id}/contacted", tags=["Opportunities"])
def mark_contacted(opp_id: int, db=Depends(get_db)):
    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(404, "Opportunity not found")
    opp.contacted = True
    db.commit()
    return {"status": "updated"}


# ── Alerts ────────────────────────────────────────────────────────────────────

@app.get("/api/alerts", tags=["Alerts"])
def list_alerts(db=Depends(get_db)):
    return [_alert_to_dict(a) for a in db.query(Alert).all()]


@app.post("/api/alerts", tags=["Alerts"])
def create_alert(data: AlertCreate, db=Depends(get_db)):
    alert = Alert(**data.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _alert_to_dict(alert)


@app.post("/api/alerts/{alert_id}/trigger", tags=["Alerts"])
def trigger_alert(
    alert_id: int, background_tasks: BackgroundTasks, db=Depends(get_db)
):
    """Manually trigger an alert — fetches latest papers and sends notification."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    background_tasks.add_task(_run_alert, alert.id, alert.topic, alert.channel)
    return {"status": "triggered"}


def _run_alert(alert_id: int, topic: str, channel: str) -> None:
    db = SessionLocal()
    try:
        papers = fetch_papers(topic, max_results=10, date_filter_days=1)
        if not papers:
            return
        if channel == "email":
            recipient = os.getenv("SMTP_USER", "")
            send_paper_alert(recipient, papers, topic)
        elif channel == "telegram":
            send_telegram_paper_alert(papers, topic)

        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.last_sent = datetime.utcnow()
            db.commit()
    finally:
        db.close()


# ── Serialisers ───────────────────────────────────────────────────────────────

def _paper_to_dict(p: Paper) -> dict:
    return {
        "id":           p.id,
        "title":        p.title,
        "authors":      json.loads(p.authors) if p.authors else [],
        "abstract":     p.abstract,
        "summary":      p.summary,
        "keywords":     json.loads(p.keywords) if p.keywords else [],
        "categories":   p.categories,
        "published":    p.published.isoformat() if p.published else None,
        "url":          p.url,
        "pdf_url":      p.pdf_url,
        "topic":        p.topic,
        "is_bookmarked": p.is_bookmarked,
    }


def _opp_to_dict(o: Opportunity) -> dict:
    return {
        "id":             o.id,
        "type":           o.type,
        "name":           o.name,
        "institution":    o.institution,
        "email":          o.email,
        "research_area":  o.research_area,
        "url":            o.url,
        "notes":          o.notes,
        "contacted":      o.contacted,
        "reply_received": o.reply_received,
        "created_at":     o.created_at.isoformat() if o.created_at else None,
    }


def _alert_to_dict(a: Alert) -> dict:
    return {
        "id":        a.id,
        "topic":     a.topic,
        "channel":   a.channel,
        "frequency": a.frequency,
        "active":    a.active,
        "last_sent": a.last_sent.isoformat() if a.last_sent else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# n8n-Optimised Endpoints  (/api/n8n/*)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/n8n/topics", tags=["n8n"])
def n8n_get_topics(db=Depends(get_db)):
    """
    Return all distinct research topics stored in the DB.
    n8n uses this to iterate workflows per-topic.
    """
    rows = db.query(Paper.topic).distinct().all()
    return [{"topic": r[0]} for r in rows if r[0]]


@app.post("/api/n8n/bulk-fetch", tags=["n8n"])
def n8n_bulk_fetch(req: BulkFetchRequest, db=Depends(get_db)):
    """
    Fetch papers for multiple topics in one call.
    n8n uses this to parallelise multi-topic monitoring without N individual requests.
    Returns per-topic result with paper list and counts.
    """
    results = []
    for topic in req.topics:
        papers = fetch_papers(
            topic,
            max_results=req.max_results,
            date_filter_days=req.date_filter_days,
        )
        saved = 0
        for p in papers:
            if not db.query(Paper).filter(Paper.id == p["id"]).first():
                summary, keywords = "", "[]"
                if req.auto_summarize:
                    try:
                        summary = summarize_paper(p["title"], p["abstract"])
                        keywords = json.dumps(extract_keywords(f"{p['title']} {p['abstract']}"))
                    except Exception as exc:
                        logger.warning(f"Bulk-fetch summarize error: {exc}")
                db.add(Paper(
                    id=p["id"], title=p["title"], authors=p["authors"],
                    abstract=p["abstract"], summary=summary, keywords=keywords,
                    categories=p.get("categories", ""),
                    published=datetime.fromisoformat(p["published"]) if p.get("published") else None,
                    url=p["url"], pdf_url=p.get("pdf_url", ""), topic=topic,
                ))
                saved += 1
        db.commit()
        results.append({
            "topic": topic,
            "count": len(papers),
            "saved": saved,
            "papers": papers,
        })
    return results


@app.get("/api/n8n/summary-stats", tags=["n8n"])
def n8n_summary_stats(db=Depends(get_db)):
    """
    Combined system statistics — consumed by n8n weekly digest workflow
    to build the report header without multiple round-trips.
    """
    total   = db.query(Paper).count()
    return {
        "total_papers":     total,
        "summarized":       db.query(Paper).filter(Paper.summary != None, Paper.summary != "").count(),
        "bookmarked":       db.query(Paper).filter(Paper.is_bookmarked == True).count(),
        "topics":           db.query(Paper.topic).distinct().count(),
        "opportunities":    db.query(Opportunity).count(),
        "un_contacted":     db.query(Opportunity).filter(Opportunity.contacted == False).count(),
        "active_alerts":    db.query(Alert).filter(Alert.active == True).count(),
        "generated_at":     datetime.utcnow().isoformat(),
    }


@app.post("/api/n8n/batch-summarize", tags=["n8n"])
def n8n_batch_summarize(req: BatchSummarizeRequest, db=Depends(get_db)):
    """
    Summarize up to `limit` papers identified by ID in one call.
    Skips papers that already have a summary. Returns enriched paper dicts.
    """
    papers = (
        db.query(Paper)
        .filter(Paper.id.in_(req.paper_ids))
        .limit(req.limit)
        .all()
    )
    results = []
    for p in papers:
        if not p.summary:
            try:
                p.summary  = summarize_paper(p.title, p.abstract)
                p.keywords = json.dumps(extract_keywords(f"{p.title} {p.abstract}"))
                db.commit()
            except Exception as exc:
                logger.warning(f"Batch summarize error {p.id}: {exc}")
        results.append(_paper_to_dict(p))
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Webhook Endpoints  (/webhook/*)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/webhook/gap-analysis", tags=["Webhooks"])
def webhook_gap_analysis(req: GapWebhookRequest, db=Depends(get_db)):
    """
    n8n calls this webhook to trigger an on-demand research gap analysis.
    Fetches latest papers for the topic, runs AI gap detection, returns JSON.
    The n8n 'Respond to Webhook' node can relay this back to the caller.
    """
    papers = (
        db.query(Paper)
        .filter(Paper.topic.ilike(f"%{req.topic}%"))
        .order_by(Paper.published.desc())
        .limit(req.max_papers)
        .all()
    )
    gaps = detect_research_gaps([_paper_to_dict(p) for p in papers], req.topic)
    return {
        "topic":        req.topic,
        "paper_count":  len(papers),
        "gaps":         gaps,
        "timestamp":    datetime.utcnow().isoformat(),
    }


@app.post("/webhook/n8n-event", tags=["Webhooks"])
def webhook_n8n_event(req: N8nEventRequest):
    """
    n8n posts execution events here (success, error, etc.).
    Enables centralised logging of n8n workflow outcomes in the API logs.
    """
    logger.info(
        f"[n8n-event] workflow={req.workflow!r} "
        f"event={req.event!r} status={req.status!r} "
        f"msg={req.message!r}"
    )
    return {"received": True, "timestamp": datetime.utcnow().isoformat()}
