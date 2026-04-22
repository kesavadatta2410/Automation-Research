"""
pages/alerts.py — Alert & Notification Configuration
"""
import streamlit as st
from utils.helpers import APIClient

client = APIClient()


def render():
    st.markdown("""
    <div class="page-header">
      <h1>🔔 Alerts & Automation</h1>
      <p>Configure daily paper alerts, weekly reports, and notification channels.</p>
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
                freq_badge = (
                    "🔄 Daily" if a["frequency"] == "daily"
                    else "📅 Weekly"
                )
                status_color = "#4aff9e" if a.get("active") else "#888"

                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"""
                        <div class="ar-card">
                          <div style="display:flex;justify-content:space-between;">
                            <div>
                              <strong>{channel_icon} {a['topic']}</strong>
                              <span class="tag" style="margin-left:8px;">{freq_badge}</span>
                              <span class="tag">{a['channel'].title()}</span>
                            </div>
                            <div style="color:{status_color};font-size:12px;">
                              ⬤ {'Active' if a.get('active') else 'Paused'}
                            </div>
                          </div>
                          {f'<div style="font-size:12px;color:#888;margin-top:6px;">Last sent: {a["last_sent"]}</div>' if a.get("last_sent") else ''}
                        </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        if st.button("▶️ Trigger Now", key=f"trigger_{a['id']}",
                                     use_container_width=True):
                            with st.spinner("Triggering alert..."):
                                try:
                                    client.trigger_alert(a["id"])
                                    st.success("Alert triggered!")
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
            ⚠️ Make sure SMTP / Telegram credentials are set in <code>.env</code> 
            before creating alerts.
            </div>
            """, unsafe_allow_html=True)

            if st.form_submit_button("🔔 Create Alert", use_container_width=True):
                if not topic:
                    st.error("Topic is required.")
                else:
                    try:
                        client.create_alert({
                            "topic": topic,
                            "channel": channel,
                            "frequency": frequency,
                        })
                        st.success(f"✅ Alert created for '{topic}' via {channel} ({frequency})")
                    except Exception as e:
                        st.error(f"Failed: {e}")

    # ── Tab 3: n8n Workflows ──────────────────────────────────────────────────
    with tab3:
        st.markdown("#### 🤖 n8n Workflow Automation")
        st.markdown("""
        <div class="ar-alert info">
        n8n handles scheduled automation — daily paper fetching, weekly digest emails, 
        and Telegram notifications without keeping the Python process running.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Available Workflow Templates")

        workflows = [
            {
                "name":    "📄 Daily Paper Alert",
                "desc":    "Runs every day at 8 AM. Fetches new papers, summarizes top 5, sends email/Telegram.",
                "trigger": "Schedule: 0 8 * * *",
                "nodes":   ["Cron Trigger", "HTTP Request (arXiv)", "AI Summarize", "Email/Telegram Send"],
                "file":    "daily_alerts.json",
            },
            {
                "name":    "📊 Weekly Research Digest",
                "desc":    "Every Monday. Aggregates weekly papers, trends, gap analysis, sends report.",
                "trigger": "Schedule: 0 9 * * 1",
                "nodes":   ["Cron Trigger", "HTTP Request (Papers)", "HTTP Request (Trends)", "Format Report", "Send Email"],
                "file":    "weekly_report.json",
            },
        ]

        for wf in workflows:
            with st.expander(wf["name"]):
                st.markdown(f"**Description:** {wf['desc']}")
                st.markdown(f"**Trigger:** `{wf['trigger']}`")
                st.markdown("**Workflow Nodes:**")
                for node in wf["nodes"]:
                    st.markdown(f"  → {node}")
                c1, c2 = st.columns(2)
                c1.download_button(
                    f"⬇️ Download {wf['file']}",
                    data=_get_workflow_json(wf["file"]),
                    file_name=wf["file"],
                    mime="application/json",
                    use_container_width=True,
                )
                c2.link_button(
                    "🚀 Open n8n",
                    "http://localhost:5678",
                    use_container_width=True,
                )

        st.markdown("---")
        st.markdown("#### Setup Instructions")
        st.markdown("""
        1. **Install n8n:** `npm install -g n8n` or use Docker: `docker run -p 5678:5678 n8nio/n8n`
        2. **Start n8n:** `n8n start`
        3. **Import templates:** Go to n8n UI → Workflows → Import → Upload JSON
        4. **Configure credentials:** Set SMTP / Telegram credentials in n8n credential store
        5. **Set webhook URL:** Update `N8N_WEBHOOK_URL` in `.env`
        6. **Enable schedules:** Activate workflows in n8n dashboard
        """)

        st.code("""
# Quick n8n Docker setup
docker run -it --rm \\
  --name n8n \\
  -p 5678:5678 \\
  -v ~/.n8n:/home/node/.n8n \\
  n8nio/n8n
        """, language="bash")


def _get_workflow_json(filename: str) -> str:
    """Return n8n workflow JSON template."""
    import json

    if filename == "daily_alerts.json":
        workflow = {
            "name": "AutoResearch — Daily Paper Alert",
            "nodes": [
                {
                    "id": "1", "name": "Schedule Trigger", "type": "n8n-nodes-base.scheduleTrigger",
                    "parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": "0 8 * * *"}]}},
                    "position": [100, 300],
                },
                {
                    "id": "2", "name": "Fetch Papers", "type": "n8n-nodes-base.httpRequest",
                    "parameters": {
                        "method": "POST", "url": "={{$env.API_BASE_URL}}/api/papers/search",
                        "jsonBody": True,
                        "body": '{"query": "{{$env.ALERT_TOPIC}}", "max_results": 10, "auto_summarize": true, "date_filter_days": 1}',
                    },
                    "position": [300, 300],
                },
                {
                    "id": "3", "name": "Send Email Alert", "type": "n8n-nodes-base.httpRequest",
                    "parameters": {
                        "method": "POST", "url": "={{$env.API_BASE_URL}}/api/alerts/1/trigger",
                    },
                    "position": [500, 300],
                },
            ],
            "connections": {
                "Schedule Trigger": {"main": [[{"node": "Fetch Papers", "type": "main", "index": 0}]]},
                "Fetch Papers": {"main": [[{"node": "Send Email Alert", "type": "main", "index": 0}]]},
            },
        }
    else:
        workflow = {
            "name": "AutoResearch — Weekly Digest",
            "nodes": [
                {
                    "id": "1", "name": "Weekly Schedule", "type": "n8n-nodes-base.scheduleTrigger",
                    "parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": "0 9 * * 1"}]}},
                    "position": [100, 300],
                },
                {
                    "id": "2", "name": "Get Papers", "type": "n8n-nodes-base.httpRequest",
                    "parameters": {"method": "GET", "url": "={{$env.API_BASE_URL}}/api/papers?limit=50"},
                    "position": [300, 200],
                },
                {
                    "id": "3", "name": "Get Trends", "type": "n8n-nodes-base.httpRequest",
                    "parameters": {"method": "GET", "url": "={{$env.API_BASE_URL}}/api/insights/trends"},
                    "position": [300, 400],
                },
            ],
            "connections": {
                "Weekly Schedule": {"main": [[
                    {"node": "Get Papers", "type": "main", "index": 0},
                    {"node": "Get Trends", "type": "main", "index": 0},
                ]]},
            },
        }

    return json.dumps(workflow, indent=2)
