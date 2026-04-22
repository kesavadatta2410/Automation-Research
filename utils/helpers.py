"""
utils/helpers.py — Shared helpers, API client, formatting utils
"""
import os
import requests
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


# ── API Client ────────────────────────────────────────────────────────────────

class APIClient:
    """Thin client for FastAPI backend."""

    def __init__(self, base_url: str = API_BASE, timeout: int = 60):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: dict = None) -> dict:
        r = requests.get(f"{self.base}{path}", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict = None) -> dict:
        r = requests.post(f"{self.base}{path}", json=data, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _patch(self, path: str) -> dict:
        r = requests.patch(f"{self.base}{path}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # Papers
    def search_papers(self, query: str, max_results: int = 20,
                      sort_by: str = "relevance",
                      auto_summarize: bool = False) -> dict:
        return self._post("/api/papers/search", {
            "query": query, "max_results": max_results,
            "sort_by": sort_by, "auto_summarize": auto_summarize,
        })

    def list_papers(self, topic: str = None, bookmarked: bool = None,
                    limit: int = 50) -> dict:
        params = {"limit": limit}
        if topic:
            params["topic"] = topic
        if bookmarked is not None:
            params["bookmarked"] = bookmarked
        return self._get("/api/papers", params)

    def summarize_paper(self, paper_id: str) -> dict:
        return self._post(f"/api/papers/{paper_id}/summarize")

    def toggle_bookmark(self, paper_id: str) -> dict:
        return self._patch(f"/api/papers/{paper_id}/bookmark")

    # Insights
    def get_trends(self, topic: str = None, limit: int = 30) -> dict:
        params = {"limit": limit}
        if topic:
            params["topic"] = topic
        return self._get("/api/insights/trends", params)

    def get_gaps(self, topic: str) -> dict:
        return self._get("/api/insights/gaps", {"topic": topic})

    # Opportunities
    def list_opportunities(self, type: str = None) -> list:
        params = {}
        if type:
            params["type"] = type
        return self._get("/api/opportunities", params)

    def create_opportunity(self, data: dict) -> dict:
        return self._post("/api/opportunities", data)

    def generate_email(self, opp_id: int, data: dict) -> dict:
        return self._post(f"/api/opportunities/{opp_id}/generate-email", data)

    def mark_contacted(self, opp_id: int) -> dict:
        return self._patch(f"/api/opportunities/{opp_id}/contacted")

    # Alerts
    def list_alerts(self) -> list:
        return self._get("/api/alerts")

    def create_alert(self, data: dict) -> dict:
        return self._post("/api/alerts", data)

    def trigger_alert(self, alert_id: int) -> dict:
        return self._post(f"/api/alerts/{alert_id}/trigger")

    def health(self) -> bool:
        try:
            self._get("/health")
            return True
        except Exception:
            return False


# ── Formatting Helpers ────────────────────────────────────────────────────────

def format_authors(authors: list, max_show: int = 3) -> str:
    if not authors:
        return "Unknown"
    shown = authors[:max_show]
    rest  = len(authors) - max_show
    result = ", ".join(shown)
    if rest > 0:
        result += f" +{rest} more"
    return result


def format_date(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso_str


def truncate(text: str, length: int = 300) -> str:
    if not text:
        return ""
    return text[:length] + "..." if len(text) > length else text


def keywords_to_tags_html(keywords: list) -> str:
    """Return HTML badge string for keywords (used in Streamlit markdown)."""
    badges = " ".join(
        f'<span style="background:#6C63FF22;color:#6C63FF;'
        f'padding:2px 8px;border-radius:12px;font-size:12px;'
        f'border:1px solid #6C63FF44;">{kw}</span>'
        for kw in keywords
    )
    return badges
