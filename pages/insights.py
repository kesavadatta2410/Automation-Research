"""
pages/insights.py — AI Insights: Trends, Gaps, Analysis
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.helpers import APIClient

client = APIClient()


def render():
    st.markdown("""
    <div class="page-header">
      <h1>🧠 AI Insights</h1>
      <p>Trend analysis, keyword mapping, and research gap detection powered by AI.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📈 Trends", "🔭 Research Gaps", "🗺️ Concept Map"])

    # ── Tab 1: Trends ─────────────────────────────────────────────────────────
    with tab1:
        c1, c2 = st.columns([3, 1])
        trend_topic = c1.text_input("Topic for trend analysis",
                                     placeholder="e.g. deep learning, genomics",
                                     key="trend_topic")
        trend_limit = c2.selectbox("Analyze papers", [20, 30, 50, 100], index=1)

        if st.button("📊 Analyze Trends", key="analyze_trends"):
            with st.spinner("Analyzing trends with AI..."):
                try:
                    data = client.get_trends(
                        topic=trend_topic or None,
                        limit=trend_limit
                    )
                    st.session_state["trend_data"] = data
                except Exception as e:
                    st.error(f"Trend analysis failed: {e}")

        if "trend_data" in st.session_state:
            _render_trends(st.session_state["trend_data"])

    # ── Tab 2: Research Gaps ──────────────────────────────────────────────────
    with tab2:
        st.markdown("#### 🔭 Research Gap Detection")
        st.markdown(
            '<div class="ar-alert info">AI analyzes recent papers to identify '
            'underexplored areas and open research questions.</div>',
            unsafe_allow_html=True,
        )

        gap_topic = st.text_input("Research topic",
                                   placeholder="e.g. federated learning privacy",
                                   key="gap_topic")
        if st.button("🔍 Detect Research Gaps", key="detect_gaps"):
            if not gap_topic:
                st.warning("Enter a topic first.")
            else:
                with st.spinner(f"Analyzing literature on '{gap_topic}'..."):
                    try:
                        data = client.get_gaps(gap_topic)
                        st.session_state["gap_data"] = data
                    except Exception as e:
                        st.error(f"Gap detection failed: {e}")

        if "gap_data" in st.session_state:
            _render_gaps(st.session_state["gap_data"])

    # ── Tab 3: Concept Map ────────────────────────────────────────────────────
    with tab3:
        st.markdown("#### 🗺️ Keyword Concept Network")
        try:
            data = client.get_trends(limit=50)
            kw_freq = data.get("keyword_frequency", {})
            if kw_freq:
                _render_concept_network(kw_freq)
            else:
                st.info("Search and save papers first to build concept map.")
        except Exception as e:
            st.info("Load some papers first to see concept network.")


# ── Sub-renderers ─────────────────────────────────────────────────────────────

def _render_trends(data: dict):
    kw_freq     = data.get("keyword_frequency", {})
    top_kws     = data.get("top_keywords", [])
    narrative   = data.get("trend_narrative", "")

    if narrative:
        st.markdown("#### 🔍 AI Trend Analysis")
        st.markdown(
            f"<div style='background:#1a2040;border-left:3px solid #6C63FF;"
            f"padding:16px;border-radius:0 8px 8px 0;line-height:1.7;color:#c0d4ff;'>"
            f"{narrative}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("")

    if kw_freq:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 📊 Keyword Frequency")
            df = pd.DataFrame(
                list(kw_freq.items())[:20],
                columns=["Keyword", "Frequency"]
            ).sort_values("Frequency", ascending=True)

            fig = px.bar(
                df, x="Frequency", y="Keyword", orientation="h",
                color="Frequency",
                color_continuous_scale=[[0, "#2a2d3e"], [1, "#6C63FF"]],
                template="plotly_dark",
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=0, b=0),
                coloraxis_showscale=False,
                yaxis_title=None,
                xaxis_title="Frequency",
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown("#### ☁️ Top Keywords")
            if top_kws:
                tags = "".join(
                    f'<span style="background:rgba(108,99,255,{0.1 + i*0.06});'
                    f'color:#6C63FF;border:1px solid rgba(108,99,255,0.4);'
                    f'padding:6px 14px;border-radius:20px;font-size:{14+i}px;'
                    f'margin:4px;display:inline-block;">{kw}</span>'
                    for i, kw in enumerate(reversed(top_kws[:10]))
                )
                st.markdown(
                    f"<div style='padding:20px;line-height:2.4;'>{tags}</div>",
                    unsafe_allow_html=True,
                )


def _render_gaps(data: dict):
    topic = data.get("topic", "")
    gaps  = data.get("gaps", [])

    st.markdown(f"#### 🔭 Research Gaps — *{topic}*")

    if not gaps:
        st.info("No gaps detected. Try searching for more papers on this topic first.")
        return

    for i, gap in enumerate(gaps, 1):
        confidence = gap.get("confidence", 0.5)
        conf_color = (
            "#4aff9e" if confidence > 0.7
            else "#ffaa4a" if confidence > 0.4
            else "#ff4a4a"
        )
        conf_pct = int(confidence * 100)

        st.markdown(f"""
        <div class="ar-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div style="flex:1;">
              <div style="font-size:16px;font-weight:600;margin-bottom:8px;">
                🔭 Gap {i}: {gap.get('gap','')}
              </div>
              <div style="color:#ccc;font-size:13px;line-height:1.6;">
                {gap.get('explanation','')}
              </div>
            </div>
            <div style="text-align:center;margin-left:20px;min-width:70px;">
              <div style="font-size:1.4rem;font-weight:700;color:{conf_color};">{conf_pct}%</div>
              <div style="font-size:11px;color:#888;">confidence</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)


def _render_concept_network(kw_freq: dict):
    """Simple bubble chart as concept network proxy."""
    items = list(kw_freq.items())[:25]
    if not items:
        return

    keywords = [i[0] for i in items]
    freqs    = [i[1] for i in items]

    fig = go.Figure(data=[go.Scatter(
        x=list(range(len(keywords))),
        y=freqs,
        mode="markers+text",
        text=keywords,
        textposition="top center",
        marker=dict(
            size=[max(10, f * 8) for f in freqs],
            color=freqs,
            colorscale=[[0, "#2a2d3e"], [0.5, "#6C63FF"], [1, "#a090ff"]],
            showscale=False,
        ),
        textfont=dict(color="#FAFAFA", size=11),
    )])

    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(title="Frequency", showgrid=True, gridcolor="#2a2d3e"),
        height=450,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)
