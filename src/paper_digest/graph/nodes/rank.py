from __future__ import annotations

from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..state import GraphState, Paper


def rank_papers(state: GraphState) -> GraphState:
    """
    Rank candidate papers using TF-IDF cosine similarity between:
      query_text = "topic1 topic2 ..."
      doc_text   = "title abstract"

    Writes:
      state["ranked"] = sorted papers (best first)
      state["rank_scores"] = list[float] aligned with ranked (optional)
    """
    topics: List[str] = state.get("topics", [])
    candidates: List[Paper] = state.get("candidates") or state.get("papers", [])

    if not candidates:
        state["ranked"] = []
        state.setdefault("logs", []).append("RankPapers(TFIDF): no candidates to rank.")
        return state

    # If no topics, keep original order (or you could sort by updated_at)
    if not topics:
        state["ranked"] = candidates
        state.setdefault("logs", []).append("RankPapers(TFIDF): no topics; kept original order.")
        return state

    query_text = " ".join([t.strip() for t in topics if t and t.strip()])

    docs = []
    for p in candidates:
        title = p.get("title", "") or ""
        abstract = p.get("abstract", "") or ""
        docs.append(f"{title}\n{abstract}")

    # Fit TF-IDF on docs + query so they share the same vocabulary
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),   # unigrams + bigrams helps phrases like "tool use"
        max_features=20000,
    )

    X = vectorizer.fit_transform(docs + [query_text])  # last row is query
    doc_vecs = X[:-1]
    query_vec = X[-1]

    sims = cosine_similarity(doc_vecs, query_vec).reshape(-1)  # length = len(candidates)

    # Sort candidates by similarity
    order = sorted(range(len(candidates)), key=lambda i: sims[i], reverse=True)
    ranked = [candidates[i] for i in order]
    ranked_scores = [float(sims[i]) for i in order]

    state["ranked"] = ranked
    state["rank_scores"] = ranked_scores  # optional, useful for debugging

    preview = [f"{ranked_scores[i]:.3f} :: {ranked[i].get('title','')[:60]}" for i in range(min(5, len(ranked)))]
    state.setdefault("logs", []).append(f"RankPapers(TFIDF): ranked {len(ranked)} papers. Top: {preview}")

    return state
