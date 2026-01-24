from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List
from urllib.parse import quote_plus

import feedparser
import requests

from ..state import GraphState, Paper


ARXIV_API = "http://export.arxiv.org/api/query"


def _build_arxiv_query(topics: List[str]) -> str:
    """
    Build arXiv search_query string.

    If topics is empty, we default to cs.AI OR cs.LG OR cs.CL.
    Otherwise we search title/abstract for your keywords.
    """
    if not topics:
        # Good default “AI-ish” categories:
        return "cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV OR cat:cs.IR"

    # Search in title+abstract
    # arXiv supports ti: and abs:
    parts = []
    for t in topics:
        t = t.strip()
        if not t:
            continue
        # Quote terms that might contain spaces
        parts.append(f'ti:"{t}" OR abs:"{t}"')

    # Combine topics with OR so it doesn't become too strict
    return " OR ".join(parts) if parts else "cat:cs.AI OR cat:cs.LG OR cat:cs.CL"

def _parse_arxiv_entry(entry) -> Paper:
    # arXiv entry.id often looks like "http://arxiv.org/abs/XXXX.XXXXXvN"
    paper_id = entry.get("id", "")
    title = (entry.get("title", "") or "").replace("\n", " ").strip()
    abstract = (entry.get("summary", "") or "").replace("\n", " ").strip()
    url = entry.get("link", "") or paper_id

    authors = [a.get("name", "").strip() for a in entry.get("authors", []) if a.get("name")]
    tags = [t.get("term", "").strip() for t in entry.get("tags", []) if t.get("term")]

    published = entry.get("published", "")
    updated = entry.get("updated", "")

    return {
        "paper_id": paper_id,
        "source": "arxiv",
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "url": url,
        "published_at": published,
        "updated_at": updated,
        "categories": tags,
    }


def fetch_papers(state: GraphState) -> GraphState:
    """
    Fetch recently UPDATED arXiv papers (Atom feed) and return as normalized `papers`.

    Notes:
    - arXiv API returns many results; we control with max_results.
    - We'll filter/dedupe later in separate nodes; for now we just fetch + normalize.
    """
    # run_date in local time format is fine for digest labeling
    state["run_date"] = state.get("run_date") or datetime.now().strftime("%Y-%m-%d")
    topics = state.get("topics", [])
    max_results = int(state.get("max_results", 20))

    search_query = _build_arxiv_query(topics)

    params = {
        "search_query": search_query,
        "sortBy": "lastUpdatedDate",
        "sortOrder": "descending",
        "start": 0,
        "max_results": max_results,
    }

    try:
        # requests → feedparser to parse Atom
        resp = requests.get(ARXIV_API, params=params, timeout=20)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)

        papers: List[Paper] = []
        for e in feed.entries:
            p = _parse_arxiv_entry(e)
            # Basic sanity: must have title + abstract
            if p.get("title") and p.get("abstract"):
                papers.append(p)

        state["papers"] = papers
        state.setdefault("logs", []).append(
            f"FetchPapers: fetched {len(papers)} papers from arXiv (sorted by lastUpdatedDate)."
        )
        return state

    except Exception as ex:
        state.setdefault("errors", []).append(f"FetchPapers failed: {ex}")
        state["papers"] = []
        state.setdefault("logs", []).append("FetchPapers: error; produced 0 papers.")
        return state
