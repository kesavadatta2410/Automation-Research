"""
backend/database.py — SQLAlchemy async DB setup
"""
from sqlalchemy import (
    Column, String, Text, DateTime, Integer,
    Boolean, Float, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./autoresearch.db")
ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

# Sync engine (for migrations / init)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine (for FastAPI)
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


# ── Models ────────────────────────────────────────────────────────────────────

class Paper(Base):
    __tablename__ = "papers"

    id           = Column(String, primary_key=True)          # arXiv ID
    title        = Column(String, nullable=False)
    authors      = Column(Text)                              # JSON list
    abstract     = Column(Text)
    summary      = Column(Text)                              # AI-generated
    keywords     = Column(Text)                              # JSON list
    categories   = Column(String)
    published    = Column(DateTime)
    url          = Column(String)
    pdf_url      = Column(String)
    topic        = Column(String)
    is_bookmarked = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)


class Trend(Base):
    __tablename__ = "trends"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    topic       = Column(String)
    keyword     = Column(String)
    frequency   = Column(Integer, default=1)
    period      = Column(String)                             # "2024-W12"
    created_at  = Column(DateTime, default=datetime.utcnow)


class ResearchGap(Base):
    __tablename__ = "research_gaps"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    topic       = Column(String)
    gap_text    = Column(Text)
    source_papers = Column(Text)                             # JSON list of IDs
    confidence  = Column(Float, default=0.0)
    created_at  = Column(DateTime, default=datetime.utcnow)


class Opportunity(Base):
    __tablename__ = "opportunities"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    type         = Column(String)                            # professor/lab/internship
    name         = Column(String)
    institution  = Column(String)
    email        = Column(String)
    research_area = Column(String)
    url          = Column(String)
    notes        = Column(Text)
    contacted    = Column(Boolean, default=False)
    reply_received = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)


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
    channel    = Column(String)                              # email/telegram
    frequency  = Column(String)                              # daily/weekly
    active     = Column(Boolean, default=True)
    last_sent  = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Init ──────────────────────────────────────────────────────────────────────

def init_db():
    """Create all tables (sync — used at startup)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Sync session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Async session dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session
