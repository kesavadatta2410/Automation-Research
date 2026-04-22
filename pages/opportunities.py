"""
pages/opportunities.py — Research Opportunities + Outreach Automation
"""
import streamlit as st
import pandas as pd
from utils.helpers import APIClient

client = APIClient()


def render():
    st.markdown("""
    <div class="page-header">
      <h1>🎯 Opportunities</h1>
      <p>Track professors, labs, and internships. Generate personalized outreach emails.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Pipeline", "➕ Add Opportunity", "✉️ Email Generator"])

    # ── Tab 1: Pipeline ───────────────────────────────────────────────────────
    with tab1:
        try:
            opps = client.list_opportunities()
        except Exception as e:
            st.error(f"Failed to load: {e}")
            opps = []

        if not opps:
            st.info("No opportunities tracked yet. Add one in the 'Add Opportunity' tab.")
        else:
            # Summary metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total",      len(opps))
            c2.metric("Professors", sum(1 for o in opps if o.get("type") == "professor"))
            c3.metric("Labs",       sum(1 for o in opps if o.get("type") == "lab"))
            c4.metric("Contacted",  sum(1 for o in opps if o.get("contacted")))

            st.markdown("---")

            # Kanban-style columns
            pending   = [o for o in opps if not o.get("contacted")]
            contacted = [o for o in opps if o.get("contacted") and not o.get("reply_received")]
            replied   = [o for o in opps if o.get("reply_received")]

            k1, k2, k3 = st.columns(3)

            with k1:
                st.markdown(f"#### ⏳ Pending ({len(pending)})")
                for o in pending:
                    _opp_card(o, show_contact_btn=True)

            with k2:
                st.markdown(f"#### ✉️ Contacted ({len(contacted)})")
                for o in contacted:
                    _opp_card(o)

            with k3:
                st.markdown(f"#### 💬 Replied ({len(replied)})")
                for o in replied:
                    _opp_card(o)

    # ── Tab 2: Add Opportunity ────────────────────────────────────────────────
    with tab2:
        st.markdown("#### Add New Opportunity")
        with st.form("add_opp_form"):
            c1, c2 = st.columns(2)
            opp_type    = c1.selectbox("Type", ["professor", "lab", "internship", "fellowship"])
            name        = c2.text_input("Name / Title *")
            institution = c1.text_input("Institution / Company *")
            email       = c2.text_input("Email")
            research    = c1.text_input("Research Area")
            url         = c2.text_input("Website URL")
            notes       = st.text_area("Notes", height=80)

            if st.form_submit_button("➕ Add Opportunity", use_container_width=True):
                if not name or not institution:
                    st.error("Name and Institution are required.")
                else:
                    try:
                        client.create_opportunity({
                            "type": opp_type, "name": name,
                            "institution": institution, "email": email,
                            "research_area": research, "url": url, "notes": notes,
                        })
                        st.success(f"✅ Added: {name} at {institution}")
                    except Exception as e:
                        st.error(f"Failed: {e}")

    # ── Tab 3: Email Generator ────────────────────────────────────────────────
    with tab3:
        st.markdown("#### ✉️ AI Outreach Email Generator")
        st.markdown(
            '<div class="ar-alert info">AI generates personalized emails '
            'tailored to each professor\'s research focus.</div>',
            unsafe_allow_html=True,
        )

        with st.form("email_gen_form"):
            c1, c2 = st.columns(2)
            prof_name   = c1.text_input("Professor Name *")
            institution = c2.text_input("Institution *")
            research    = c1.text_input("Research Area *")
            your_name   = c2.text_input("Your Name *")
            background  = st.text_area(
                "Your Background *",
                placeholder="E.g. I am a 3rd year PhD student at XYZ University, "
                            "with expertise in machine learning and NLP...",
                height=100,
            )
            gen_btn = st.form_submit_button("⚡ Generate Email", use_container_width=True)

        if gen_btn:
            required = [prof_name, institution, research, your_name, background]
            if not all(required):
                st.error("All fields are required.")
            else:
                with st.spinner("Generating personalized email with AI..."):
                    try:
                        from services.ai_service import generate_outreach_email
                        result = generate_outreach_email(
                            professor_name=prof_name,
                            institution=institution,
                            research_area=research,
                            your_background=background,
                            your_name=your_name,
                        )
                        st.session_state["generated_email"] = result
                    except Exception as e:
                        st.error(f"Email generation failed: {e}")

        if "generated_email" in st.session_state:
            email_data = st.session_state["generated_email"]
            st.markdown("---")
            st.markdown("#### 📧 Generated Email")

            col1, col2 = st.columns([4, 1])
            with col1:
                subject = st.text_input("Subject", value=email_data.get("subject",""))
                body = st.text_area("Email Body", value=email_data.get("body",""), height=300)
            with col2:
                st.markdown("<br><br><br>", unsafe_allow_html=True)
                if st.button("📋 Copy Subject", use_container_width=True):
                    st.write(f"`{subject}`")
                st.download_button(
                    "⬇️ Download",
                    data=f"Subject: {subject}\n\n{body}",
                    file_name=f"outreach_{prof_name.replace(' ','_')}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )


# ── Card component ────────────────────────────────────────────────────────────

def _opp_card(opp: dict, show_contact_btn: bool = False):
    type_icon = {"professor": "👨‍🏫", "lab": "🔬", "internship": "💼", "fellowship": "🏆"}.get(
        opp.get("type",""), "🎯"
    )
    st.markdown(f"""
    <div class="ar-card" style="margin-bottom:12px;">
      <div style="font-weight:600;">{type_icon} {opp['name']}</div>
      <div style="color:#888;font-size:13px;">{opp.get('institution','')}</div>
      {f'<div style="color:#6C63FF;font-size:12px;margin-top:4px;">{opp.get("research_area","")}</div>' if opp.get("research_area") else ''}
      {f'<div style="font-size:12px;color:#aaa;margin-top:4px;">📧 {opp["email"]}</div>' if opp.get("email") else ''}
    </div>
    """, unsafe_allow_html=True)

    if show_contact_btn:
        if st.button(f"✅ Mark Contacted", key=f"contact_{opp['id']}", use_container_width=True):
            try:
                client.mark_contacted(opp["id"])
                st.rerun()
            except Exception as e:
                st.error(str(e))
