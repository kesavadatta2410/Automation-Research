"""
services/notification_service.py — Email (SMTP) + Telegram alerts
"""
import os
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Optional
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST      = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT      = int(os.getenv("SMTP_PORT", 587))
SMTP_USER      = os.getenv("SMTP_USER", "")
SMTP_PASSWORD  = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM     = os.getenv("EMAIL_FROM", "AutoResearch AI <noreply@autoresearch.ai>")
TG_TOKEN       = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID", "")


# ── Email ─────────────────────────────────────────────────────────────────────

def _build_paper_alert_html(papers: List[dict], topic: str) -> str:
    rows = ""
    for p in papers[:10]:
        authors = json.loads(p.get("authors", "[]")) if isinstance(p.get("authors"), str) else []
        author_str = ", ".join(authors[:3]) + ("..." if len(authors) > 3 else "")
        rows += f"""
        <tr>
          <td style="padding:12px;border-bottom:1px solid #2a2d3e;">
            <a href="{p.get('url','#')}" style="color:#6C63FF;font-weight:600;text-decoration:none;">
              {p.get('title','Untitled')}
            </a><br>
            <small style="color:#aaa;">{author_str}</small><br>
            <p style="color:#ccc;margin:6px 0;font-size:13px;">
              {p.get('summary', p.get('abstract',''))[:200]}...
            </p>
          </td>
        </tr>"""

    return f"""
    <html><body style="background:#0E1117;color:#FAFAFA;font-family:sans-serif;padding:20px;">
      <div style="max-width:700px;margin:auto;">
        <h2 style="color:#6C63FF;">🔬 AutoResearch AI — Daily Alert</h2>
        <p>Topic: <strong>{topic}</strong> · {datetime.now().strftime('%B %d, %Y')}</p>
        <p>{len(papers)} new papers found.</p>
        <table style="width:100%;border-collapse:collapse;">{rows}</table>
        <p style="color:#888;font-size:12px;margin-top:20px;">
          Sent by AutoResearch AI · <a href="#" style="color:#6C63FF;">Unsubscribe</a>
        </p>
      </div>
    </body></html>"""


def send_email(
    to: str,
    subject: str,
    body_html: str,
    body_text: str = "",
) -> bool:
    """Send HTML email via SMTP."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = EMAIL_FROM
        msg["To"]      = to
        msg["Subject"] = subject
        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to, msg.as_string())

        logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def send_paper_alert(to: str, papers: List[dict], topic: str) -> bool:
    html = _build_paper_alert_html(papers, topic)
    return send_email(
        to=to,
        subject=f"📄 AutoResearch — {len(papers)} new papers on '{topic}'",
        body_html=html,
    )


def send_outreach_email(to: str, subject: str, body: str) -> bool:
    html = f"""
    <html><body style="font-family:sans-serif;line-height:1.6;padding:20px;">
      {body.replace(chr(10), '<br>')}
      <hr style="margin-top:30px;border-color:#eee;">
      <small style="color:#888;">Sent via AutoResearch AI</small>
    </body></html>"""
    return send_email(to=to, subject=subject, body_html=html, body_text=body)


# ── Telegram ──────────────────────────────────────────────────────────────────

def send_telegram(message: str) -> bool:
    """Send Telegram message via Bot API."""
    if not TG_TOKEN or not TG_CHAT_ID:
        logger.warning("Telegram not configured")
        return False
    try:
        import requests
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {
            "chat_id":    TG_CHAT_ID,
            "text":       message,
            "parse_mode": "Markdown",
        }
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        logger.info("Telegram message sent")
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def send_telegram_paper_alert(papers: List[dict], topic: str) -> bool:
    lines = [f"🔬 *AutoResearch AI — Daily Alert*", f"Topic: `{topic}`\n"]
    for i, p in enumerate(papers[:5], 1):
        lines.append(f"{i}. [{p['title']}]({p.get('url','#')})")
    if len(papers) > 5:
        lines.append(f"\n_...and {len(papers)-5} more papers_")
    lines.append(f"\nTotal: *{len(papers)} papers* found today.")
    return send_telegram("\n".join(lines))
