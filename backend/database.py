"""
backend/database.py — SQLAlchemy ORM setup (sync, SQLite default)
"""
from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./autoresearch.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── ORM Base ──────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Models ────────────────────────────────────────────────────────────────────

class Paper(Base):
    __tablename__ = "papers"

    id            = Column(String,   primary_key=True)   # arXiv ID
    title         = Column(String,   nullable=False)
    authors       = Column(Text)                         # JSON list
    abstract      = Column(Text)
    summary       = Column(Text)                         # AI-generated summary
    keywords      = Column(Text)                         # JSON list
    categories    = Column(String)
    published     = Column(DateTime)
    url           = Column(String)
    pdf_url       = Column(String)
    topic         = Column(String)
    is_bookmarked = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)


class Trend(Base):
    __tablename__ = "trends"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    topic      = Column(String)
    keyword    = Column(String)
    frequency  = Column(Integer, default=1)
    period     = Column(String)       # e.g. "2024-W12"
    created_at = Column(DateTime, default=datetime.utcnow)


class ResearchGap(Base):
    __tablename__ = "research_gaps"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    topic         = Column(String)
    gap_text      = Column(Text)
    source_papers = Column(Text)      # JSON list of IDs
    confidence    = Column(Float, default=0.0)
    created_at    = Column(DateTime, default=datetime.utcnow)


class Opportunity(Base):
    __tablename__ = "opportunities"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    type           = Column(String)   # professor | lab | internship | fellowship
    name           = Column(String)
    institution    = Column(String)
    email          = Column(String)
    research_area  = Column(String)
    url            = Column(String)
    notes          = Column(Text)
    contacted      = Column(Boolean, default=False)
    reply_received = Column(Boolean, default=False)
    created_at     = Column(DateTime, default=datetime.utcnow)


class OutreachEmail(Base):
    __tablename__ = "outreach_emails"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer)
    subject        = Column(String)
    body           = Column(Text)
    sent           = Column(Boolean, default=False)
    sent_at        = Column(DateTime)
    created_at     = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    topic      = Column(String)
    channel    = Column(String)    # email | telegram
    frequency  = Column(String)   # daily | weekly
    active     = Column(Boolean, default=True)
    last_sent  = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Helpers ───────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables (idempotent — safe to call on every startup)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: yields a sync SQLAlchemy session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
