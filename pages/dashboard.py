"""
pages/dashboard.py — AutoResearch AI Dashboard
"""
import streamlit as st
from utils.helpers import APIClient, format_date, truncate, format_authors

client = APIClient()


def render():
    st.markdown("""
    <div class="page-header">
      <h1>🏠 Dashboard</h1>
      <p>Welcome to AutoResearch AI — your intelligent research automation platform.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Metrics ───────────────────────────────────────────────────────────────
    try:
        papers_data = client.list_papers(limit=200)
        total_papers    = papers_data.get("total", 0)
        papers          = papers_data.get("papers", [])
        summarized      = sum(1 for p in papers if p.get("summary"))
        bookmarked      = sum(1 for p in papers if p.get("is_bookmarked"))
        topics          = len(set(p.get("topic","") for p in papers if p.get("topic")))
    except Exception:
        total_papers = summarized = bookmarked = topics = 0
        papers = []

    try:
        opps = client.list_opportunities()
        total_opps   = len(opps)
        contacted    = sum(1 for o in opps if o.get("contacted"))
    except Exception:
        total_opps = contacted = 0
        opps = []

    cols = st.columns(5)
    metrics = [
        ("📄", total_papers,   "Total Papers"),
        ("🧠", summarized,     "Summarized"),
        ("🔖", bookmarked,     "Bookmarked"),
        ("🎯", total_opps,     "Opportunities"),
        ("✉️", contacted,      "Contacted"),
    ]
    for col, (icon, val, lbl) in zip(cols, metrics):
        col.markdown(f"""
        <div class="metric-tile">
          <div style="font-size:1.5rem;">{icon}</div>
          <div class="val">{val}</div>
          <div class="lbl">{lbl}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Quick Search ──────────────────────────────────────────────────────────
    st.markdown("### ⚡ Quick Search")
    with st.form("quick_search"):
        c1, c2, c3 = st.columns([4, 1, 1])
        query = c1.text_input("Search topic", placeholder="e.g. large language models, CRISPR, quantum computing")
        max_r = c2.selectbox("Results", [10, 20, 50], index=1)
        submitted = c3.form_submit_button("🔍 Search", use_container_width=True)

    if submitted and query:
        with st.spinner(f"Searching arXiv for '{query}'..."):
            try:
                result = client.search_papers(query, max_results=max_r)
                st.success(result.get("message", "Done!"))
                st.session_state["last_search_papers"] = result.get("papers", [])
                st.session_state["last_search_query"] = query
            except Exception as e:
                st.error(f"Search failed: {e}")

    if "last_search_papers" in st.session_state:
        _render_paper_list(
            st.session_state["last_search_papers"],
            title=f"Results: {st.session_state.get('last_search_query','')}"
        )

    # ── Recent Papers ─────────────────────────────────────────────────────────
    if papers and "last_search_papers" not in st.session_state:
        st.markdown("---")
        _render_paper_list(papers[:8], title="📚 Recently Fetched Papers")

    # ── Recent Opportunities ──────────────────────────────────────────────────
    if opps:
        st.markdown("---")
        st.markdown("### 🎯 Recent Opportunities")
        cols = st.columns(min(len(opps[:3]), 3))
        for col, opp in zip(cols, opps[:3]):
            with col:
                status = "✅ Contacted" if opp.get("contacted") else "⏳ Pending"
                st.markdown(f"""
                <div class="ar-card">
                  <div style="font-weight:600;">{opp['name']}</div>
                  <div style="color:#888;font-size:13px;">{opp.get('institution','')}</div>
                  <div style="margin-top:8px;">
                    <span class="tag">{opp.get('type','').title()}</span>
                    <span class="tag">{status}</span>
                  </div>
                </div>""", unsafe_allow_html=True)


def _render_paper_list(papers: list, title: str = "Papers"):
    if not papers:
        st.info("No papers found.")
        return
    st.markdown(f"### {title}")
    for p in papers:
        authors = p.get("authors", [])
        if isinstance(authors, str):
            import json
            authors = json.loads(authors)

        with st.expander(f"📄 {p['title'][:90]}{'...' if len(p['title'])>90 else ''}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**Authors:** {format_authors(authors)}")
                st.markdown(f"**Published:** {format_date(p.get('published',''))}")
                st.markdown(f"**Topic:** `{p.get('topic','')}`")
                if p.get("categories"):
                    st.markdown(f"**Categories:** {p['categories']}")

                st.markdown("**Abstract:**")
                st.markdown(f"<p style='color:#ccc;font-size:13px;'>{truncate(p.get('abstract',''),400)}</p>",
                            unsafe_allow_html=True)

                if p.get("summary"):
                    st.markdown("**🧠 AI Summary:**")
                    st.markdown(f"<p style='color:#aef;font-size:13px;border-left:3px solid #6C63FF;"
                                f"padding-left:12px;'>{p['summary']}</p>",
                                unsafe_allow_html=True)

                kws = p.get("keywords", [])
                if kws:
                    tags = " ".join(f'<span class="tag">{k}</span>' for k in kws)
                    st.markdown(tags, unsafe_allow_html=True)

            with c2:
                if p.get("url"):
                    st.link_button("🔗 View Paper", p["url"])
                if p.get("pdf_url"):
                    st.link_button("📄 PDF", p["pdf_url"])
