"""
services/scheduler.py — Lightweight Python scheduler (n8n alternative)
Run with: python services/scheduler.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import schedule
import time
import json
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

from backend.database import SessionLocal, init_db, Alert, Paper
from services.arxiv_service import fetch_papers
from services.notification_service import (
    send_paper_alert, send_telegram_paper_alert,
    send_email,
)
from services.ai_service import analyze_trends


def run_daily_alert(alert_id: int, topic: str, channel: str):
    """Fetch papers from last 24h and notify."""
    logger.info(f"[Alert {alert_id}] Running daily alert: '{topic}' → {channel}")
    db = SessionLocal()
    try:
        papers = fetch_papers(topic, max_results=10, date_filter_days=1)
        if not papers:
            logger.info(f"[Alert {alert_id}] No new papers found.")
            return

        recipient = os.getenv("SMTP_USER", "")
        if channel == "email" and recipient:
            ok = send_paper_alert(recipient, papers, topic)
            logger.info(f"[Alert {alert_id}] Email sent: {ok}")
        elif channel == "telegram":
            ok = send_telegram_paper_alert(papers, topic)
            logger.info(f"[Alert {alert_id}] Telegram sent: {ok}")

        # Update last_sent
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.last_sent = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.error(f"[Alert {alert_id}] Failed: {e}")
    finally:
        db.close()


def run_weekly_digest():
    """Build and send weekly research digest."""
    logger.info("Running weekly digest...")
    db = SessionLocal()
    try:
        papers = db.query(Paper).order_by(Paper.published.desc()).limit(50).all()
        paper_dicts = [
            {
                "title":    p.title,
                "abstract": p.abstract,
                "url":      p.url,
                "topic":    p.topic,
            }
            for p in papers
        ]

        trend_data = analyze_trends(paper_dicts)
        top_kws    = trend_data.get("top_keywords", [])
        narrative  = trend_data.get("trend_narrative", "")

        html = f"""
        <html><body style="font-family:sans-serif;background:#f5f7ff;padding:32px;max-width:700px;margin:auto">
          <div style="background:linear-gradient(135deg,#6C63FF,#4a42cc);color:white;
                      padding:32px;border-radius:16px;margin-bottom:24px">
            <h1 style="margin:0">🔬 AutoResearch AI</h1>
            <h2 style="margin:8px 0 0;opacity:.9">Weekly Research Digest</h2>
            <p style="opacity:.7;margin:8px 0 0">{datetime.now().strftime('%A, %B %d, %Y')}</p>
          </div>

          <div style="background:white;border-radius:12px;padding:24px;margin-bottom:16px;
                      box-shadow:0 2px 8px rgba(0,0,0,.08)">
            <h3 style="color:#6C63FF;margin-top:0">📄 Library Stats</h3>
            <p>Total papers in library: <strong>{len(papers)}</strong></p>
          </div>

          <div style="background:white;border-radius:12px;padding:24px;margin-bottom:16px;
                      box-shadow:0 2px 8px rgba(0,0,0,.08)">
            <h3 style="color:#6C63FF;margin-top:0">🔑 Trending Keywords</h3>
            <p>{" · ".join(top_kws)}</p>
          </div>

          {"<div style='background:white;border-radius:12px;padding:24px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,.08)'><h3 style='color:#6C63FF;margin-top:0'>🔭 AI Trend Analysis</h3><p style='color:#444;line-height:1.6'>" + narrative + "</p></div>" if narrative else ""}

          <p style="color:#aaa;font-size:12px;text-align:center">Sent by AutoResearch AI</p>
        </body></html>"""

        recipient = os.getenv("SMTP_USER", "")
        if recipient:
            send_email(
                to=recipient,
                subject=f"📊 AutoResearch Weekly Digest — {datetime.now().strftime('%B %d, %Y')}",
                body_html=html,
            )

        # Telegram summary
        from services.notification_service import send_telegram
        send_telegram(
            f"📊 *AutoResearch AI — Weekly Digest*\n\n"
            f"📄 Papers in library: *{len(papers)}*\n"
            f"🔑 Top keywords: {', '.join(top_kws[:6])}"
        )

    except Exception as e:
        logger.error(f"Weekly digest failed: {e}")
    finally:
        db.close()


def load_and_schedule_alerts():
    """Load active alerts from DB and register schedules."""
    db = SessionLocal()
    try:
        alerts = db.query(Alert).filter(Alert.active == True).all()
        for a in alerts:
            if a.frequency == "daily":
                schedule.every().day.at("08:00").do(
                    run_daily_alert, alert_id=a.id, topic=a.topic, channel=a.channel
                )
                logger.info(f"Scheduled daily alert: '{a.topic}' → {a.channel}")
            elif a.frequency == "weekly":
                schedule.every().monday.at("09:00").do(
                    run_daily_alert, alert_id=a.id, topic=a.topic, channel=a.channel
                )
                logger.info(f"Scheduled weekly alert: '{a.topic}' → {a.channel}")

        # Weekly digest always runs Monday 9AM
        schedule.every().monday.at("09:00").do(run_weekly_digest)
        logger.info("Weekly digest scheduled: Monday 09:00")
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("AutoResearch AI Scheduler starting...")
    init_db()
    load_and_schedule_alerts()

    logger.info(f"Active jobs: {len(schedule.jobs)}")
    logger.info("Scheduler running. Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(60)
