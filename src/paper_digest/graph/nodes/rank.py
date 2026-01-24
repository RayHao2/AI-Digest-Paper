from __future__ import annotations

import re
from typing import List

from rank_bm25 import BM25Okapi

from ..state import GraphState, Paper


_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    """
    Lightweight tokenizer:
    - lowercase
    - keep alphanumerics
    - split into tokens

    Example:
      "Prompt-Guided Diffusion-Based Medical Image Segmentation"
      -> ["prompt", "guided", "diffusion", "based", "medical", "image", "segmentation"]
    """
    return _WORD_RE.findall((text or "").lower())


def rank_papers(state: GraphState) -> GraphState:
    """
    Rank papers using BM25 between:
      query_tokens = tokens("topic1 topic2 ...")
      doc_tokens   = tokens("title abstract")

    Writes:
      state["ranked"] = sorted papers (best first)
      state["rank_scores"] = list[float] aligned with ranked (BM25 scores)
    """
    topics: List[str] = state.get("topics", [])
    papers: List[Paper] = state.get("papers", [])

    if not papers:
        state["ranked"] = []
        state["rank_scores"] = []
        state.setdefault("logs", []).append("RankPapers(BM25): no papers to rank.")
        return state

    # If no topics, keep fetched order (already sorted by lastUpdatedDate in fetch)
    if not topics:
        state["ranked"] = papers
        state["rank_scores"] = [0.0] * len(papers)
        state.setdefault("logs", []).append(
            f"RankPapers(BM25): no topics; kept fetched order ({len(papers)} papers)."
        )
        return state

    query_text = " ".join(t.strip() for t in topics if t and t.strip())
    query_tokens = _tokenize(query_text)

    if not query_tokens:
        state["ranked"] = papers
        state["rank_scores"] = [0.0] * len(papers)
        state.setdefault("logs", []).append(
            f"RankPapers(BM25): empty query; kept fetched order ({len(papers)} papers)."
        )
        return state

    # Build tokenized corpus
    corpus_tokens: List[List[str]] = []
    for p in papers:
        title = p.get("title") or ""
        abstract = p.get("abstract") or ""
        corpus_tokens.append(_tokenize(f"{title}\n{abstract}"))

    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(query_tokens)  # numpy array-like, len == len(papers)

    order = sorted(range(len(papers)), key=lambda i: float(scores[i]), reverse=True)
    ranked = [papers[i] for i in order]
    ranked_scores = [float(scores[i]) for i in order]

    state["ranked"] = ranked
    state["rank_scores"] = ranked_scores

    preview = [
        f"{ranked_scores[i]:.3f} :: {ranked[i].get('title','')[:60]}"
        for i in range(min(5, len(ranked)))
    ]
    state.setdefault("logs", []).append(
        f"RankPapers(BM25): ranked {len(ranked)} papers using query='{query_text}'. Top: {preview}"
    )
    return state
