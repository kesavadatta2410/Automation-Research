"""
pages/discovery.py — Paper Discovery & Management
"""
import streamlit as st
import pandas as pd
import json
from utils.helpers import APIClient, format_date, format_authors, truncate

client = APIClient()


def render():
    st.markdown("""
    <div class="page-header">
      <h1>📄 Paper Discovery</h1>
      <p>Search and manage research papers from arXiv and other sources.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔍 Search", "📚 Library", "🔖 Bookmarks"])

    # ── Tab 1: Search ─────────────────────────────────────────────────────────
    with tab1:
        with st.form("search_form"):
            st.markdown("#### Search Parameters")
            c1, c2 = st.columns([3, 1])
            query = c1.text_input(
                "Query / Keywords",
                placeholder="e.g. 'transformer attention mechanism' or 'CRISPR gene editing'"
            )
            max_results = c2.slider("Max Results", 5, 100, 20)

            c3, c4, c5 = st.columns(3)
            sort_by = c3.selectbox(
                "Sort By",
                ["relevance", "submittedDate", "lastUpdatedDate"],
                format_func=lambda x: {
                    "relevance":       "Relevance",
                    "submittedDate":   "Date Submitted",
                    "lastUpdatedDate": "Last Updated",
                }[x]
            )
            date_filter = c4.selectbox(
                "Date Filter",
                [None, 7, 30, 90, 365],
                format_func=lambda x: "All Time" if x is None else f"Last {x} days"
            )
            auto_sum = c5.checkbox("Auto Summarize", value=False,
                                   help="Use AI to summarize each paper (slower)")

            search_btn = st.form_submit_button("🔍 Search arXiv", use_container_width=True)

        if search_btn and query:
            with st.spinner(f"Searching arXiv for '{query}'..."):
                try:
                    result = client.search_papers(
                        query, max_results=max_results,
                        sort_by=sort_by, auto_summarize=auto_sum,
                    )
                    papers = result.get("papers", [])
                    st.success(result.get("message", f"Found {len(papers)} papers"))
                    st.session_state["discovery_papers"] = papers
                    st.session_state["discovery_query"] = query
                except Exception as e:
                    st.error(f"Search error: {e}")

        if "discovery_papers" in st.session_state:
            papers = st.session_state["discovery_papers"]
            _render_paper_cards(papers)

    # ── Tab 2: Library ────────────────────────────────────────────────────────
    with tab2:
        st.markdown("#### All Saved Papers")

        # Filter bar
        fc1, fc2, fc3 = st.columns([2, 1, 1])
        filter_topic = fc1.text_input("Filter by topic", key="lib_topic")
        lib_limit    = fc3.selectbox("Show", [20, 50, 100, 200], key="lib_limit")
        refresh_btn  = fc2.button("🔄 Refresh", key="lib_refresh")

        try:
            data   = client.list_papers(
                topic=filter_topic or None,
                limit=lib_limit,
            )
            papers = data.get("papers", [])
            total  = data.get("total", 0)

            st.markdown(f"**{total}** papers in library")

            # Table view toggle
            view = st.radio("View", ["Cards", "Table"], horizontal=True, key="lib_view")

            if view == "Table":
                _render_paper_table(papers)
            else:
                _render_paper_cards(papers, show_summarize_btn=True)
        except Exception as e:
            st.error(f"Failed to load library: {e}")

    # ── Tab 3: Bookmarks ──────────────────────────────────────────────────────
    with tab3:
        st.markdown("#### Bookmarked Papers")
        try:
            data   = client.list_papers(bookmarked=True, limit=50)
            papers = data.get("papers", [])
            if not papers:
                st.info("No bookmarked papers yet. Click the bookmark button on any paper.")
            else:
                st.success(f"{len(papers)} bookmarked papers")
                _render_paper_cards(papers, show_summarize_btn=True)
        except Exception as e:
            st.error(f"Failed to load bookmarks: {e}")


# ── Sub-components ────────────────────────────────────────────────────────────

def _render_paper_cards(papers: list, show_summarize_btn: bool = False):
    if not papers:
        st.info("No papers to display.")
        return

    for p in papers:
        authors = p.get("authors", [])
        if isinstance(authors, str):
            authors = json.loads(authors)

        with st.expander(f"📄 {p['title'][:85]}{'...' if len(p['title'])>85 else ''}"):
            left, right = st.columns([4, 1])
            with left:
                meta = f"👤 {format_authors(authors)}  ·  📅 {format_date(p.get('published',''))}  ·  🏷️ {p.get('categories','')}"
                st.markdown(f"<small style='color:#888;'>{meta}</small>", unsafe_allow_html=True)

                st.markdown("**Abstract**")
                st.markdown(
                    f"<p style='color:#ccc;font-size:13px;line-height:1.6;'>"
                    f"{truncate(p.get('abstract',''), 500)}</p>",
                    unsafe_allow_html=True,
                )

                if p.get("summary"):
                    st.markdown("**🧠 AI Summary**")
                    st.markdown(
                        f"<div style='background:#1a2040;border-left:3px solid #6C63FF;"
                        f"padding:12px;border-radius:0 8px 8px 0;font-size:13px;"
                        f"color:#c0d4ff;line-height:1.6;'>{p['summary']}</div>",
                        unsafe_allow_html=True,
                    )

                kws = p.get("keywords", [])
                if isinstance(kws, str):
                    kws = json.loads(kws)
                if kws:
                    tags = "".join(f'<span class="tag">{k}</span> ' for k in kws)
                    st.markdown(f"<div style='margin-top:8px;'>{tags}</div>",
                                unsafe_allow_html=True)

            with right:
                if p.get("url"):
                    st.link_button("🔗 Paper", p["url"], use_container_width=True)
                if p.get("pdf_url"):
                    st.link_button("📄 PDF", p["pdf_url"], use_container_width=True)

                bk_label = "🔖 Unbookmark" if p.get("is_bookmarked") else "🔖 Bookmark"
                if st.button(bk_label, key=f"bk_{p['id']}", use_container_width=True):
                    try:
                        client.toggle_bookmark(p["id"])
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

                if show_summarize_btn and not p.get("summary"):
                    if st.button("🧠 Summarize", key=f"sum_{p['id']}", use_container_width=True):
                        with st.spinner("Generating summary..."):
                            try:
                                result = client.summarize_paper(p["id"])
                                st.success("Summarized!")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))


def _render_paper_table(papers: list):
    rows = []
    for p in papers:
        authors = p.get("authors", [])
        if isinstance(authors, str):
            authors = json.loads(authors)
        rows.append({
            "Title":      p.get("title","")[:70],
            "Authors":    format_authors(authors, 2),
            "Published":  format_date(p.get("published","")),
            "Topic":      p.get("topic",""),
            "Categories": p.get("categories",""),
            "Summarized": "✅" if p.get("summary") else "—",
            "Bookmarked": "🔖" if p.get("is_bookmarked") else "—",
            "URL":        p.get("url",""),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=500)
