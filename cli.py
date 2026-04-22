"""
cli.py — AutoResearch AI Command Line Interface
Usage: python cli.py <command> [options]
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import argparse
import json
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


def cmd_fetch(args):
    """Fetch papers for a topic."""
    from services.arxiv_service import fetch_papers
    from backend.database import init_db, SessionLocal, Paper
    from services.ai_service import summarize_paper, extract_keywords
    from datetime import datetime

    init_db()
    db = SessionLocal()

    logger.info(f"Fetching papers: '{args.query}' (max={args.max})")
    papers = fetch_papers(args.query, max_results=args.max)

    saved = 0
    for p in papers:
        if not db.query(Paper).filter(Paper.id == p["id"]).first():
            summary  = ""
            keywords = "[]"
            if args.summarize:
                logger.info(f"Summarizing: {p['title'][:50]}...")
                summary  = summarize_paper(p["title"], p["abstract"])
                kw_list  = extract_keywords(f"{p['title']} {p['abstract']}")
                keywords = json.dumps(kw_list)

            obj = Paper(
                id=p["id"], title=p["title"], authors=p["authors"],
                abstract=p["abstract"], summary=summary, keywords=keywords,
                categories=p.get("categories",""),
                published=datetime.fromisoformat(p["published"]) if p.get("published") else None,
                url=p["url"], pdf_url=p.get("pdf_url",""),
                topic=args.query,
            )
            db.add(obj)
            saved += 1

    db.commit()
    db.close()
    print(f"✅ Fetched {len(papers)} papers, saved {saved} new.")


def cmd_summarize_all(args):
    """Summarize all papers missing summaries."""
    from backend.database import init_db, SessionLocal, Paper
    from services.ai_service import summarize_paper, extract_keywords

    init_db()
    db = SessionLocal()
    papers = db.query(Paper).filter(
        (Paper.summary == None) | (Paper.summary == "")
    ).all()

    logger.info(f"Summarizing {len(papers)} papers...")
    for i, p in enumerate(papers):
        try:
            p.summary  = summarize_paper(p.title, p.abstract)
            kw_list    = extract_keywords(f"{p.title} {p.abstract}")
            p.keywords = json.dumps(kw_list)
            db.commit()
            print(f"[{i+1}/{len(papers)}] ✅ {p.title[:60]}")
        except Exception as e:
            print(f"[{i+1}/{len(papers)}] ❌ {p.title[:60]}: {e}")

    db.close()
    print("Done.")


def cmd_trends(args):
    """Print trend analysis for a topic."""
    from backend.database import init_db, SessionLocal, Paper
    from services.ai_service import analyze_trends

    init_db()
    db = SessionLocal()
    q = db.query(Paper)
    if args.topic:
        q = q.filter(Paper.topic.ilike(f"%{args.topic}%"))
    papers = [{"title": p.title, "abstract": p.abstract} for p in q.limit(50).all()]
    db.close()

    result = analyze_trends(papers)
    print("\n📈 TOP KEYWORDS:")
    for kw, freq in list(result["keyword_frequency"].items())[:15]:
        bar = "█" * min(freq, 30)
        print(f"  {kw:25s} {bar} ({freq})")

    if result.get("trend_narrative"):
        print("\n🔍 AI TREND ANALYSIS:")
        print(result["trend_narrative"])


def cmd_gaps(args):
    """Detect research gaps for a topic."""
    from backend.database import init_db, SessionLocal, Paper
    from services.ai_service import detect_research_gaps

    init_db()
    db = SessionLocal()
    papers = [
        {"title": p.title, "abstract": p.abstract}
        for p in db.query(Paper)
                   .filter(Paper.topic.ilike(f"%{args.topic}%"))
                   .limit(15).all()
    ]
    db.close()

    gaps = detect_research_gaps(papers, args.topic)
    print(f"\n🔭 RESEARCH GAPS — {args.topic}")
    for i, g in enumerate(gaps, 1):
        conf = int(g.get("confidence", 0) * 100)
        print(f"\n  {i}. {g['gap']} [{conf}% confidence]")
        print(f"     {g.get('explanation','')}")


def cmd_stats(args):
    """Print database statistics."""
    from backend.database import init_db, SessionLocal, Paper, Opportunity, Alert

    init_db()
    db = SessionLocal()

    total_papers  = db.query(Paper).count()
    summarized    = db.query(Paper).filter(Paper.summary != "", Paper.summary != None).count()
    bookmarked    = db.query(Paper).filter(Paper.is_bookmarked == True).count()
    topics        = db.query(Paper.topic).distinct().count()
    opportunities = db.query(Opportunity).count()
    alerts        = db.query(Alert).count()
    db.close()

    print("\n📊 AutoResearch AI — Database Stats")
    print(f"  Papers:        {total_papers}")
    print(f"  Summarized:    {summarized} ({int(summarized/max(total_papers,1)*100)}%)")
    print(f"  Bookmarked:    {bookmarked}")
    print(f"  Topics:        {topics}")
    print(f"  Opportunities: {opportunities}")
    print(f"  Alerts:        {alerts}")


def cmd_alert_now(args):
    """Trigger an alert immediately."""
    from services.scheduler import run_daily_alert
    from backend.database import init_db, SessionLocal, Alert

    init_db()
    db = SessionLocal()
    alert = db.query(Alert).filter(Alert.id == args.id).first()
    db.close()

    if not alert:
        print(f"❌ Alert {args.id} not found.")
        return

    print(f"⚡ Triggering alert {args.id}: '{alert.topic}' → {alert.channel}")
    run_daily_alert(alert.id, alert.topic, alert.channel)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AutoResearch AI CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  fetch         Fetch papers from arXiv
  summarize     Summarize all unsummarized papers
  trends        Show keyword trends
  gaps          Detect research gaps
  stats         Show DB statistics
  alert         Trigger an alert now

Examples:
  python cli.py fetch --query "graph neural networks" --max 30 --summarize
  python cli.py trends --topic "deep learning"
  python cli.py gaps --topic "federated learning"
  python cli.py stats
  python cli.py alert --id 1
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    # fetch
    p_fetch = subparsers.add_parser("fetch", help="Fetch papers from arXiv")
    p_fetch.add_argument("--query",     required=True, help="Search query")
    p_fetch.add_argument("--max",       type=int, default=20, help="Max results")
    p_fetch.add_argument("--summarize", action="store_true", help="Auto-summarize papers")

    # summarize
    subparsers.add_parser("summarize", help="Summarize all papers without summaries")

    # trends
    p_trends = subparsers.add_parser("trends", help="Show keyword trends")
    p_trends.add_argument("--topic", default=None, help="Filter by topic")

    # gaps
    p_gaps = subparsers.add_parser("gaps", help="Detect research gaps")
    p_gaps.add_argument("--topic", required=True, help="Research topic")

    # stats
    subparsers.add_parser("stats", help="Show database stats")

    # alert
    p_alert = subparsers.add_parser("alert", help="Trigger an alert now")
    p_alert.add_argument("--id", type=int, required=True, help="Alert ID")

    args = parser.parse_args()

    dispatch = {
        "fetch":     cmd_fetch,
        "summarize": cmd_summarize_all,
        "trends":    cmd_trends,
        "gaps":      cmd_gaps,
        "stats":     cmd_stats,
        "alert":     cmd_alert_now,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
