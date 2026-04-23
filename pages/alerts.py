"""
pages/alerts.py — Alert & Notification Configuration + n8n Integration
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests
import streamlit as st
from utils.helpers import APIClient

client = APIClient()
N8N_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")

_WORKFLOWS = [
    {
        "id": "ar-wf-001",
        "file": "01_daily_paper_alert.json",
        "icon": "📄",
        "name": "Daily Paper Alert",
        "trigger": "Every day at 08:00",
        "desc": "Fetches new papers for ALL active topics in parallel, AI-summarizes top results, sends rich HTML email + Telegram.",
        "nodes": ["Schedule Trigger", "GET /api/n8n/topics", "Bulk Fetch", "Format HTML", "IF Has Papers", "Email Send", "Telegram"],
    },
    {
        "id": "ar-wf-002",
        "file": "02_weekly_digest.json",
        "icon": "📊",
        "name": "Weekly Research Digest",
        "trigger": "Every Monday at 09:00",
        "desc": "Full research report: library stats + AI trend analysis + keyword cloud. Sends premium HTML email + Telegram summary.",
        "nodes": ["Schedule Trigger", "GET Summary Stats", "GET Trends", "Merge", "Format Digest", "Email Send", "Telegram", "Log Event"],
    },
    {
        "id": "ar-wf-003",
        "file": "03_multi_topic_monitor.json",
        "icon": "🚨",
        "name": "Multi-Topic Hourly Monitor",
        "trigger": "Every 1 hour",
        "desc": "Smart monitor — only fires if ≥3 new papers appear in any topic within 24h. Zero noise, maximum signal. Telegram only.",
        "nodes": ["Schedule Trigger", "GET Topics", "Bulk Fetch (24h)", "Filter ≥3 Papers", "IF Hot Topics", "Telegram"],
    },
    {
        "id": "ar-wf-004",
        "file": "04_research_gap_webhook.json",
        "icon": "🔭",
        "name": "Research Gap Webhook",
        "trigger": "HTTP POST → n8n webhook URL",
        "desc": "On-demand gap analysis. POST {topic} to the n8n webhook URL → fetches papers → AI gap detection → JSON response + Telegram.",
        "nodes": ["Webhook Trigger", "Validate Input", "Fetch Papers", "AI Gap Analysis", "Format Report", "Respond to Webhook", "Telegram"],
    },
    {
        "id": "ar-wf-005",
        "file": "05_outreach_pipeline.json",
        "icon": "✉️",
        "name": "Outreach Email Pipeline",
        "trigger": "Every Tuesday at 10:00",
        "desc": "Reads all un-contacted opportunities with emails, generates personalized AI emails for each, sends via SMTP, marks as contacted. 2s delay between sends.",
        "nodes": ["Schedule Trigger", "GET Opportunities", "Filter Has Email", "Split (1 at a time)", "AI Generate Email", "Email Send", "PATCH Contacted", "Wait 2s"],
    },
]


def _load_workflow_json(filename: str) -> str:
    wf_path = Path(__file__).parent.parent / "n8n" / "workflows" / filename
    if wf_path.exists():
        return wf_path.read_text(encoding="utf-8")
    return json.dumps({"error": "Workflow file not found", "file": filename})


def _n8n_online() -> bool:
    try:
        r = requests.get(f"{N8N_URL}/healthz", timeout=2)
        return r.status_code == 200
    except Exception:
        try:
            r = requests.get(N8N_URL, timeout=2)
            return r.status_code in (200, 302, 401)
        except Exception:
            return False


def render():
    st.markdown("""
    <div class="page-header">
      <h1>🔔 Alerts & n8n Automation</h1>
      <p>Configure alerts, manage n8n workflows, and automate your research intelligence pipeline.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Active Alerts", "➕ New Alert", "🤖 n8n Workflows"])

    # ── Tab 1: Active Alerts ──────────────────────────────────────────────────
    with tab1:
        try:
            alerts = client.list_alerts()
        except Exception:
            alerts = []

        if not alerts:
            st.info("No alerts configured. Create one in the 'New Alert' tab.")
        else:
            for a in alerts:
                channel_icon = "📧" if a["channel"] == "email" else "📱"
                freq_badge   = "🔄 Daily" if a["frequency"] == "daily" else "📅 Weekly"
                status_color = "#4aff9e" if a.get("active") else "#888"

                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"""
                    <div class="ar-card">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                          <strong>{channel_icon} {a['topic']}</strong>
                          <span class="tag" style="margin-left:8px;">{freq_badge}</span>
                          <span class="tag">{a['channel'].title()}</span>
                        </div>
                        <div style="color:{status_color};font-size:12px;">⬤ {'Active' if a.get('active') else 'Paused'}</div>
                      </div>
                      {f'<div style="font-size:12px;color:#888;margin-top:6px;">Last sent: {a["last_sent"]}</div>' if a.get("last_sent") else ''}
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    if st.button("▶️ Trigger", key=f"trigger_{a['id']}", use_container_width=True):
                        with st.spinner("Triggering..."):
                            try:
                                client.trigger_alert(a["id"])
                                st.success("Triggered!")
                            except Exception as e:
                                st.error(str(e))

    # ── Tab 2: New Alert ──────────────────────────────────────────────────────
    with tab2:
        st.markdown("#### Create New Alert")
        with st.form("new_alert_form"):
            c1, c2, c3 = st.columns(3)
            topic     = c1.text_input("Topic *", placeholder="e.g. reinforcement learning")
            channel   = c2.selectbox("Channel", ["email", "telegram"])
            frequency = c3.selectbox("Frequency", ["daily", "weekly"])
            st.markdown("""
            <div class="ar-alert warning">
            ⚠️ Make sure SMTP / Telegram credentials are set in <code>.env</code> before creating alerts.
            </div>""", unsafe_allow_html=True)
            if st.form_submit_button("🔔 Create Alert", use_container_width=True):
                if not topic:
                    st.error("Topic is required.")
                else:
                    try:
                        client.create_alert({"topic": topic, "channel": channel, "frequency": frequency})
                        st.success(f"✅ Alert created for '{topic}' via {channel} ({frequency})")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

    # ── Tab 3: n8n Workflows ──────────────────────────────────────────────────
    with tab3:
        # ── n8n Status Banner ────────────────────────────────────────────────
        online = _n8n_online()
        if online:
            st.markdown(f"""
            <div style="background:#1a3a2a;border:1px solid #4aff9e44;border-radius:10px;
                        padding:14px 18px;margin-bottom:20px;display:flex;
                        justify-content:space-between;align-items:center;">
              <span style="color:#4aff9e;font-weight:600;">⬤ n8n Online</span>
              <a href="{N8N_URL}" target="_blank"
                 style="background:#6C63FF;color:white;padding:6px 16px;border-radius:6px;
                        text-decoration:none;font-size:13px;">Open n8n Editor →</a>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#2a1a1a;border:1px solid #ff4a4a44;border-radius:10px;
                        padding:14px 18px;margin-bottom:20px;">
              <span style="color:#ff4a4a;font-weight:600;">⬤ n8n Offline</span>
              <span style="color:#888;font-size:13px;margin-left:12px;">
                Start n8n: <code>npx n8n start</code> or <code>n8n start</code>
              </span>
            </div>""", unsafe_allow_html=True)

        # ── Setup Instructions ───────────────────────────────────────────────
        with st.expander("⚙️ n8n Setup (one-time)", expanded=not online):
            st.markdown("#### Install n8n (no Docker required)")
            st.code("""
# Install globally via npm (requires Node.js 18+)
npm install -g n8n

# Start n8n — opens at http://localhost:5678
n8n start

# Or run directly without installing globally
npx n8n start
            """, language="bash")

            st.markdown("#### Connect to AutoResearch AI")
            st.markdown("""
1. Open **http://localhost:5678** in your browser
2. Create a free n8n account (local only — no cloud)
3. Go to **Workflows → Import** and upload any JSON below
4. In n8n, go to **Credentials** and add:
   - **SMTP** credential → use your `.env` SMTP settings
   - **Telegram API** → use your bot token from `.env`
5. Open the workflow → click **Active** toggle → done!
            """)

            st.markdown("#### Environment Variables in n8n")
            st.info("n8n reads env vars from your shell. Set these before starting n8n:")
            st.code("""
set SMTP_USER=your@gmail.com
set TELEGRAM_CHAT_ID=your_chat_id
n8n start
            """, language="batch")

        st.markdown("---")
        st.markdown("### 📦 Available Workflows")
        st.markdown("Download any workflow → import into n8n → set credentials → activate.")

        # ── Workflow Cards ───────────────────────────────────────────────────
        for wf in _WORKFLOWS:
            with st.container():
                st.markdown(f"""
                <div class="ar-card" style="margin-bottom:4px;">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div style="flex:1;">
                      <div style="font-size:1.1rem;font-weight:700;margin-bottom:6px;">
                        {wf['icon']} {wf['name']}
                      </div>
                      <div style="color:#888;font-size:12px;margin-bottom:8px;">
                        ⏱️ <strong>Trigger:</strong> {wf['trigger']}
                      </div>
                      <div style="color:#ccc;font-size:13px;line-height:1.6;">
                        {wf['desc']}
                      </div>
                      <div style="margin-top:10px;">
                        {''.join(f'<span class="tag">{n}</span>' for n in wf['nodes'])}
                      </div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                dl_col, open_col = st.columns([2, 1])
                with dl_col:
                    st.download_button(
                        f"⬇️ Download {wf['file']}",
                        data=_load_workflow_json(wf["file"]),
                        file_name=wf["file"],
                        mime="application/json",
                        key=f"dl_{wf['id']}",
                        use_container_width=True,
                    )
                with open_col:
                    st.link_button(
                        "🚀 Open n8n",
                        N8N_URL,
                        use_container_width=True,
                    )
                st.markdown("")

        # ── API Endpoints for n8n ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🔌 n8n-Optimised API Endpoints")
        st.markdown("These endpoints are built specifically for n8n consumption:")

        endpoints = [
            ("GET",  "/api/n8n/topics",         "All distinct research topics as array — use with Split node"),
            ("POST", "/api/n8n/bulk-fetch",      "Fetch papers for multiple topics in one call"),
            ("GET",  "/api/n8n/summary-stats",   "Combined stats for digest report header"),
            ("POST", "/api/n8n/batch-summarize", "AI-summarize up to N papers in one call"),
            ("POST", "/webhook/gap-analysis",    "On-demand AI gap analysis (called by WF-04)"),
            ("POST", "/webhook/n8n-event",       "Log n8n execution events into API logs"),
        ]

        rows = ""
        for method, path, desc in endpoints:
            color = {"GET": "#4aff9e", "POST": "#6C63FF", "PATCH": "#ffaa4a"}.get(method, "#fff")
            rows += f"""<tr>
              <td style="padding:8px 12px;"><span style="color:{color};font-weight:700;font-size:12px;">{method}</span></td>
              <td style="padding:8px 12px;font-family:monospace;color:#FAFAFA;">{path}</td>
              <td style="padding:8px 12px;color:#aaa;font-size:13px;">{desc}</td>
            </tr>"""

        st.markdown(f"""
        <div style="background:#1A1D27;border:1px solid #2a2d3e;border-radius:10px;overflow:hidden;">
          <table style="width:100%;border-collapse:collapse;">
            <thead>
              <tr style="background:#16192a;border-bottom:1px solid #2a2d3e;">
                <th style="padding:10px 12px;text-align:left;color:#888;font-size:12px;">METHOD</th>
                <th style="padding:10px 12px;text-align:left;color:#888;font-size:12px;">ENDPOINT</th>
                <th style="padding:10px 12px;text-align:left;color:#888;font-size:12px;">PURPOSE</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("")
        c1, c2 = st.columns(2)
        c1.link_button("📚 API Docs (Swagger)", "http://localhost:8000/docs",  use_container_width=True)
        c2.link_button("📄 API Docs (ReDoc)",   "http://localhost:8000/redoc", use_container_width=True)

        # ── Gap Analysis Quick Test ──────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🔭 Test Gap Webhook Live")
        st.markdown("Simulate WF-04 by triggering gap analysis directly:")
        with st.form("gap_webhook_test"):
            test_topic = st.text_input("Topic", placeholder="e.g. federated learning privacy")
            if st.form_submit_button("⚡ Run Gap Analysis", use_container_width=True):
                if not test_topic:
                    st.error("Enter a topic.")
                else:
                    with st.spinner("Running AI gap analysis..."):
                        try:
                            r = requests.post(
                                "http://localhost:8000/webhook/gap-analysis",
                                json={"topic": test_topic, "max_papers": 10},
                                timeout=60,
                            )
                            r.raise_for_status()
                            data = r.json()
                            st.success(f"Analysed {data.get('paper_count', 0)} papers. Found {len(data.get('gaps', []))} gaps.")
                            for i, g in enumerate(data.get("gaps", []), 1):
                                conf = int(g.get("confidence", 0.5) * 100)
                                st.markdown(f"""
                                <div class="ar-card">
                                  <strong>Gap {i}: {g.get('gap','')}</strong>
                                  <span class="tag" style="float:right;">{conf}% confidence</span>
                                  <br><small style="color:#aaa;">{g.get('explanation','')}</small>
                                </div>""", unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Failed: {e}")
