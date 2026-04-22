"""
services/arxiv_service.py — Fetch papers from arXiv API
"""
import arxiv
import json
from datetime import datetime
from typing import List, Optional
from loguru import logger


def fetch_papers(
    query: str,
    max_results: int = 20,
    sort_by: str = "relevance",       # relevance | lastUpdatedDate | submittedDate
    date_filter_days: Optional[int] = None,
) -> List[dict]:
    """
    Search arXiv and return list of paper dicts.
    """
    sort_map = {
        "relevance":       arxiv.SortCriterion.Relevance,
        "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
        "submittedDate":   arxiv.SortCriterion.SubmittedDate,
    }
    criterion = sort_map.get(sort_by, arxiv.SortCriterion.Relevance)

    client = arxiv.Client(page_size=max_results, delay_seconds=1, num_retries=3)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=criterion,
    )

    papers = []
    try:
        for result in client.results(search):
            published_dt = result.published
            if date_filter_days:
                from datetime import timezone, timedelta
                cutoff = datetime.now(timezone.utc) - timedelta(days=date_filter_days)
                if published_dt < cutoff:
                    continue

            paper = {
                "id":         result.entry_id.split("/")[-1],
                "title":      result.title,
                "authors":    json.dumps([a.name for a in result.authors]),
                "abstract":   result.summary.replace("\n", " "),
                "categories": ", ".join(result.categories),
                "published":  published_dt.isoformat(),
                "url":        result.entry_id,
                "pdf_url":    result.pdf_url,
                "topic":      query,
            }
            papers.append(paper)
    except Exception as e:
        logger.error(f"arXiv fetch error: {e}")

    logger.info(f"Fetched {len(papers)} papers for '{query}'")
    return papers


def fetch_paper_by_id(arxiv_id: str) -> Optional[dict]:
    """Fetch single paper by arXiv ID."""
    client = arxiv.Client()
    search = arxiv.Search(id_list=[arxiv_id])
    try:
        result = next(client.results(search))
        return {
            "id":       result.entry_id.split("/")[-1],
            "title":    result.title,
            "authors":  json.dumps([a.name for a in result.authors]),
            "abstract": result.summary.replace("\n", " "),
            "categories": ", ".join(result.categories),
            "published": result.published.isoformat(),
            "url":      result.entry_id,
            "pdf_url":  result.pdf_url,
        }
    except StopIteration:
        return None
    except Exception as e:
        logger.error(f"Fetch by ID error: {e}")
        return None
