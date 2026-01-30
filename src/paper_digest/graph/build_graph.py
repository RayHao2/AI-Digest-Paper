from __future__ import annotations

from langgraph.graph import StateGraph, END

from .state import GraphState
from .nodes.fetch import fetch_papers
from .nodes.rank import rank_papers
from .nodes.fetch_full_text_topk import fetch_full_text
from .nodes.summarize import summarize_topk
from .nodes.assemble import assemble_digest
from .nodes.persist import persist_run


def build():
    """
    Workflow:
      FetchPapers -> RankPapers -> FetchFullText -> SummarizeTopK -> AssembleDigest -> PersistRun -> END
    """
    g = StateGraph(GraphState)

    g.add_node("FetchPapers", fetch_papers)
    g.add_node("RankPapers", rank_papers)
    g.add_node("FetchFullText", fetch_full_text)
    g.add_node("SummarizeTopK", summarize_topk)
    g.add_node("AssembleDigest", assemble_digest)
    g.add_node("PersistRun", persist_run)

    g.set_entry_point("FetchPapers")

    g.add_edge("FetchPapers", "RankPapers")
    g.add_edge("RankPapers", "FetchFullText")
    g.add_edge("FetchFullText", "SummarizeTopK")
    g.add_edge("SummarizeTopK", "AssembleDigest")
    g.add_edge("AssembleDigest", "PersistRun")
    g.add_edge("PersistRun", END)

    return g.compile()
