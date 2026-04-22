"""
backend/main.py — FastAPI application entry point
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
from loguru import logger

from backend.database import get_db, init_db, SessionLocal
from backend.database import Paper, Trend, ResearchGap, Opportunity, OutreachEmail, Alert
from services.arxiv_service import fetch_papers
from services.ai_service import (
    summarize_paper, extract_keywords, analyze_trends,
    detect_research_gaps, generate_outreach_email,
)
from services.notification_service import send_paper_alert, send_telegram_paper_alert

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AutoResearch AI",
    description="Intelligent Research Automation Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    logger.info("AutoResearch AI API started ✓")


# ── Schemas ───────────────────────────────────────────────────────────────────

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
    channel: str      # email | telegram
    frequency: str    # daily | weekly


# ── Routes: Papers ────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/papers/search")
def search_papers(req: SearchRequest, db=Depends(get_db)):
    """Fetch papers from arXiv and store in DB."""
    papers = fetch_papers(
        query=req.query,
        max_results=req.max_results,
        sort_by=req.sort_by,
        date_filter_days=req.date_filter_days,
    )

    saved = 0
    for p in papers:
        existing = db.query(Paper).filter(Paper.id == p["id"]).first()
        if not existing:
            summary = ""
            keywords = "[]"
            if req.auto_summarize:
                try:
                    summary  = summarize_paper(p["title"], p["abstract"])
                    kw_list  = extract_keywords(f"{p['title']} {p['abstract']}")
                    keywords = json.dumps(kw_list)
                except Exception as e:
                    logger.warning(f"Auto-summarize failed for {p['id']}: {e}")

            paper_obj = Paper(
                id=p["id"],
                title=p["title"],
                authors=p["authors"],
                abstract=p["abstract"],
                summary=summary,
                keywords=keywords,
                categories=p.get("categories",""),
                published=datetime.fromisoformat(p["published"]) if p.get("published") else None,
                url=p["url"],
                pdf_url=p.get("pdf_url",""),
                topic=req.query,
            )
            db.add(paper_obj)
            saved += 1

    db.commit()
    return {"message": f"Fetched {len(papers)} papers, saved {saved} new.", "papers": papers}


@app.get("/api/papers")
def list_papers(
    topic: Optional[str] = None,
    bookmarked: Optional[bool] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db=Depends(get_db),
):
    q = db.query(Paper)
    if topic:
        q = q.filter(Paper.topic.ilike(f"%{topic}%"))
    if bookmarked is not None:
        q = q.filter(Paper.is_bookmarked == bookmarked)
    total = q.count()
    papers = q.order_by(Paper.published.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "papers": [_paper_to_dict(p) for p in papers],
    }


@app.get("/api/papers/{paper_id}")
def get_paper(paper_id: str, db=Depends(get_db)):
    p = db.query(Paper).filter(Paper.id == paper_id).first()
    if not p:
        raise HTTPException(404, "Paper not found")
    return _paper_to_dict(p)


@app.post("/api/papers/{paper_id}/summarize")
def summarize(paper_id: str, db=Depends(get_db)):
    p = db.query(Paper).filter(Paper.id == paper_id).first()
    if not p:
        raise HTTPException(404, "Paper not found")
    p.summary  = summarize_paper(p.title, p.abstract)
    kw_list    = extract_keywords(f"{p.title} {p.abstract}")
    p.keywords = json.dumps(kw_list)
    db.commit()
    return {"summary": p.summary, "keywords": kw_list}


@app.patch("/api/papers/{paper_id}/bookmark")
def toggle_bookmark(paper_id: str, db=Depends(get_db)):
    p = db.query(Paper).filter(Paper.id == paper_id).first()
    if not p:
        raise HTTPException(404, "Paper not found")
    p.is_bookmarked = not p.is_bookmarked
    db.commit()
    return {"bookmarked": p.is_bookmarked}


# ── Routes: AI Insights ───────────────────────────────────────────────────────

@app.get("/api/insights/trends")
def get_trends(topic: Optional[str] = None, limit: int = 30, db=Depends(get_db)):
    q = db.query(Paper)
    if topic:
        q = q.filter(Paper.topic.ilike(f"%{topic}%"))
    papers = q.order_by(Paper.published.desc()).limit(limit).all()
    paper_dicts = [_paper_to_dict(p) for p in papers]
    return analyze_trends(paper_dicts)


@app.get("/api/insights/gaps")
def get_gaps(topic: str, db=Depends(get_db)):
    papers = db.query(Paper).filter(
        Paper.topic.ilike(f"%{topic}%")
    ).order_by(Paper.published.desc()).limit(15).all()
    paper_dicts = [_paper_to_dict(p) for p in papers]
    gaps = detect_research_gaps(paper_dicts, topic)
    return {"topic": topic, "gaps": gaps}


# ── Routes: Opportunities ─────────────────────────────────────────────────────

@app.get("/api/opportunities")
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


@app.post("/api/opportunities")
def create_opportunity(data: OpportunityCreate, db=Depends(get_db)):
    opp = Opportunity(**data.dict())
    db.add(opp)
    db.commit()
    db.refresh(opp)
    return _opp_to_dict(opp)


@app.post("/api/opportunities/{opp_id}/generate-email")
def gen_email(opp_id: int, req: OutreachRequest, db=Depends(get_db)):
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
    email = OutreachEmail(
        opportunity_id=opp_id,
        subject=result["subject"],
        body=result["body"],
    )
    db.add(email)
    db.commit()
    return result


@app.patch("/api/opportunities/{opp_id}/contacted")
def mark_contacted(opp_id: int, db=Depends(get_db)):
    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(404, "Opportunity not found")
    opp.contacted = True
    db.commit()
    return {"status": "updated"}


# ── Routes: Alerts ────────────────────────────────────────────────────────────

@app.get("/api/alerts")
def list_alerts(db=Depends(get_db)):
    return [_alert_to_dict(a) for a in db.query(Alert).all()]


@app.post("/api/alerts")
def create_alert(data: AlertCreate, db=Depends(get_db)):
    alert = Alert(**data.dict())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _alert_to_dict(alert)


@app.post("/api/alerts/{alert_id}/trigger")
def trigger_alert(alert_id: int, background_tasks: BackgroundTasks, db=Depends(get_db)):
    """Manually trigger an alert (fetch + notify)."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    background_tasks.add_task(_run_alert, alert.id, alert.topic, alert.channel)
    return {"status": "triggered"}


def _run_alert(alert_id: int, topic: str, channel: str):
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


# ── Serializers ───────────────────────────────────────────────────────────────

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
        "id":            o.id,
        "type":          o.type,
        "name":          o.name,
        "institution":   o.institution,
        "email":         o.email,
        "research_area": o.research_area,
        "url":           o.url,
        "notes":         o.notes,
        "contacted":     o.contacted,
        "reply_received": o.reply_received,
        "created_at":    o.created_at.isoformat() if o.created_at else None,
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
