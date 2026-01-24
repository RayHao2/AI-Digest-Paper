from __future__ import annotations
from typing import List
from ..state import GraphState, Paper


def _matches_topics(p: Paper, topics: List[str]) -> bool:
    """Case-insensitive keyword match against title + abstract."""
    if not topics:
        return True

    hay = f"{p.get('title','')} {p.get('abstract','')}".lower()
    for t in topics:
        t = (t or "").strip().lower()
        if not t:
            continue
        if t in hay:
            return True
    return False


def filter_candidates(state: GraphState) -> GraphState:
    """
    Filter papers based on user topics (keywords). Writes `candidates`.

    MVP behavior:
    - If topics provided: keep papers where any topic appears in title/abstract
    - If no topics: keep everything (we'll do smarter defaults later)
    """
    papers: List[Paper] = state.get("papers", [])
    topics: List[str] = state.get("topics", [])

    before = len(papers)
    kept = [p for p in papers if _matches_topics(p, topics)]
    state["candidates"] = kept

    state.setdefault("logs", []).append(
        f"FilterCandidates: kept {len(kept)}/{before} papers "
        + (f"using topics={topics}." if topics else "(no topics provided).")
    )
    return state
