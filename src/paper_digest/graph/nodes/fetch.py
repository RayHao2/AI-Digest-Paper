from __future__ import annotations

from datetime import datetime
from typing import List
import time

import feedparser
import requests

from ..state import GraphState, Paper


ARXIV_API = "https://export.arxiv.org/api/query"


def _build_arxiv_query(topics: List[str]) -> str:
    """
    Build arXiv search_query string.

    If topics is empty, default to several AI-related categories.
    Otherwise search title/abstract for the provided keywords.
    """
    if not topics:
        return "cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV OR cat:cs.IR"

    parts = []
    for t in topics:
        t = t.strip()
        if not t:
            continue
        parts.append(f'ti:"{t}" OR abs:"{t}"')

    return " OR ".join(parts) if parts else "cat:cs.AI OR cat:cs.LG OR cat:cs.CL"


def _parse_arxiv_entry(entry) -> Paper:
    paper_id = entry.get("id", "")
    title = (entry.get("title", "") or "").replace("\n", " ").strip()
    abstract = (entry.get("summary", "") or "").replace("\n", " ").strip()
    url = entry.get("link", "") or paper_id

    authors = [
        a.get("name", "").strip()
        for a in entry.get("authors", [])
        if a.get("name")
    ]
    tags = [
        t.get("term", "").strip()
        for t in entry.get("tags", [])
        if t.get("term")
    ]

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
    Fetch recently updated arXiv papers and normalize them into `papers`.

    Retry on transient network failures with exponential backoff.
    """
    state["run_date"] = state.get("run_date") or datetime.now().strftime("%Y-%m-%d")
    topics = state.get("topics", [])
    max_results = int(state.get("max_results", 20))

    # Configurable knobs
    timeout_s = float(state.get("fetch_timeout_s", 45))
    max_tries = int(state.get("fetch_max_tries", 3))
    backoff_base_s = float(state.get("fetch_backoff_base_s", 2.0))

    search_query = _build_arxiv_query(topics)

    params = {
        "search_query": search_query,
        "sortBy": "lastUpdatedDate",
        "sortOrder": "descending",
        "start": 0,
        "max_results": max_results,
    }

    last_err: Exception | None = None

    for attempt in range(1, max_tries + 1):
        try:
            resp = requests.get(ARXIV_API, params=params, timeout=timeout_s)
            resp.raise_for_status()

            feed = feedparser.parse(resp.text)

            papers: List[Paper] = []
            for e in feed.entries:
                p = _parse_arxiv_entry(e)
                if p.get("title") and p.get("abstract"):
                    papers.append(p)

            state["papers"] = papers
            state.setdefault("logs", []).append(
                f"FetchPapers: fetched {len(papers)} papers from arXiv "
                f"(sorted by lastUpdatedDate, attempt {attempt}/{max_tries})."
            )
            return state

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as ex:
            last_err = ex
            if attempt < max_tries:
                sleep_s = backoff_base_s ** (attempt - 1)
                state.setdefault("logs", []).append(
                    f"FetchPapers: transient network error on attempt "
                    f"{attempt}/{max_tries}: {ex}. Retrying in {sleep_s:.1f}s."
                )
                time.sleep(sleep_s)
                continue
            break

        except requests.exceptions.HTTPError as ex:
            last_err = ex
            status = ex.response.status_code if ex.response is not None else None

            # Retry only on server-side / rate-limit style errors
            if status in {429, 500, 502, 503, 504} and attempt < max_tries:
                sleep_s = backoff_base_s ** (attempt - 1)
                state.setdefault("logs", []).append(
                    f"FetchPapers: HTTP {status} on attempt "
                    f"{attempt}/{max_tries}. Retrying in {sleep_s:.1f}s."
                )
                time.sleep(sleep_s)
                continue
            break

        except Exception as ex:
            last_err = ex
            break

    state.setdefault("errors", []).append(f"FetchPapers failed: {last_err}")
    state["papers"] = []
    state.setdefault("logs", []).append("FetchPapers: error; produced 0 papers.")
    return state