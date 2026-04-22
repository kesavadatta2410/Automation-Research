"""
app.py — AutoResearch AI · Main Streamlit Entry Point
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="AutoResearch AI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0E1117 0%, #1A1D27 100%);
    border-right: 1px solid #2a2d3e;
}
[data-testid="stSidebar"] .block-container { padding-top: 1rem; }

/* ── Cards ── */
.ar-card {
    background: #1A1D27;
    border: 1px solid #2a2d3e;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    transition: border-color 0.2s;
}
.ar-card:hover { border-color: #6C63FF55; }

/* ── Metric tiles ── */
.metric-tile {
    background: linear-gradient(135deg, #1A1D27, #16192a);
    border: 1px solid #2a2d3e;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}
.metric-tile .val { font-size: 2rem; font-weight: 700; color: #6C63FF; }
.metric-tile .lbl { font-size: 0.8rem; color: #888; margin-top: 4px; }

/* ── Tags ── */
.tag {
    display: inline-block;
    background: rgba(108,99,255,0.15);
    color: #6C63FF;
    border: 1px solid rgba(108,99,255,0.3);
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 12px;
    margin: 2px;
}

/* ── Buttons ── */
div[data-testid="stButton"] > button {
    border-radius: 8px;
    border: 1px solid #6C63FF44;
    background: rgba(108,99,255,0.1);
    color: #FAFAFA;
    transition: all 0.2s;
}
div[data-testid="stButton"] > button:hover {
    background: rgba(108,99,255,0.25);
    border-color: #6C63FF;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] select,
textarea {
    background: #1A1D27 !important;
    border: 1px solid #2a2d3e !important;
    border-radius: 8px !important;
    color: #FAFAFA !important;
}

/* ── Dividers ── */
hr { border-color: #2a2d3e !important; }

/* ── Alert boxes ── */
.ar-alert {
    padding: 12px 16px;
    border-radius: 8px;
    margin: 8px 0;
    font-size: 14px;
}
.ar-alert.info    { background: #1a2a4a; border-left: 3px solid #4a9eff; }
.ar-alert.success { background: #1a3a2a; border-left: 3px solid #4aff9e; }
.ar-alert.warning { background: #3a2a1a; border-left: 3px solid #ffaa4a; }

/* ── Page title ── */
.page-header {
    background: linear-gradient(135deg, #1A1D27 0%, #0e1117 100%);
    border: 1px solid #2a2d3e;
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
}
.page-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; }
.page-header p  { margin: 8px 0 0; color: #888; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0e1117; }
::-webkit-scrollbar-thumb { background: #2a2d3e; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar Nav ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:16px 0 24px;">
      <div style="font-size:2rem;">🔬</div>
      <div style="font-size:1.1rem;font-weight:700;color:#6C63FF;">AutoResearch AI</div>
      <div style="font-size:0.75rem;color:#888;">Research Automation Platform</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Navigation**")

    pages = {
        "🏠 Dashboard":        "dashboard",
        "📄 Paper Discovery":  "discovery",
        "🧠 AI Insights":      "insights",
        "🎯 Opportunities":    "opportunities",
        "🔔 Alerts":           "alerts",
        "⚙️ Settings":         "settings",
    }

    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    for label, key in pages.items():
        active = st.session_state.page == key
        style = "color:#6C63FF;font-weight:600;" if active else "color:#aaa;"
        if st.sidebar.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.markdown("---")
    # API status
    from utils.helpers import APIClient
    client = APIClient()
    api_ok = client.health()
    status_color = "#4aff9e" if api_ok else "#ff4a4a"
    status_text  = "API Online" if api_ok else "API Offline"
    st.markdown(
        f'<div style="font-size:12px;color:{status_color};">⬤ {status_text}</div>',
        unsafe_allow_html=True,
    )
    if not api_ok:
        st.markdown(
            '<div style="font-size:11px;color:#888;margin-top:4px;">'
            'Start: <code>uvicorn backend.main:app</code></div>',
            unsafe_allow_html=True,
        )


# ── Route to page module ──────────────────────────────────────────────────────
page = st.session_state.get("page", "dashboard")

if page == "dashboard":
    import pages.dashboard as _pg
elif page == "discovery":
    import pages.discovery as _pg
elif page == "insights":
    import pages.insights as _pg
elif page == "opportunities":
    import pages.opportunities as _pg
elif page == "alerts":
    import pages.alerts as _pg
elif page == "settings":
    import pages.settings as _pg
else:
    st.error("Page not found")
    st.stop()

_pg.render()
