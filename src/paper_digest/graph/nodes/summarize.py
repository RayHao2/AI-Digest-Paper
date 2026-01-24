from __future__ import annotations

from typing import List

from ..state import GraphState, Paper, PaperSummary


def summarize_topk(state: GraphState) -> GraphState:
    """
    MVP stub: Generate placeholder summaries for top_k papers.
    Later, this becomes an LLM call with structured output.
    """
    papers: List[Paper] = state.get("ranked") or state.get("candidates") or state.get("papers", [])
    top_k = int(state.get("top_k", 5))

    selected = papers[:top_k]
    summaries: List[PaperSummary] = []

    for p in selected:
        summaries.append(
            {
                "paper_id": p.get("paper_id", ""),
                "title": p.get("title", ""),
                "one_liner": f"Stub summary: {p.get('title', '')}",
                "key_contributions": [
                    "Demonstrates a multi-step workflow structure",
                    "Shows how state flows across nodes",
                ],
                "methods": ["LangGraph-style state machine (stub)"],
                "limitations": ["Not a real LLM summary yet"],
                "why_it_matters": "Serves as an MVP placeholder while we wire the pipeline end-to-end.",
                "tags": p.get("categories", []),
                "url": p.get("url", ""),
                "status": "ok",
            }
        )

    state["summaries"] = summaries
    state.setdefault("logs", []).append(
        f"SummarizeTopK: produced {len(summaries)} summaries (stub), "
        f"top_k={top_k}, input={'candidates' if state.get('candidates') is not None else 'papers'}."
    )

    return state
