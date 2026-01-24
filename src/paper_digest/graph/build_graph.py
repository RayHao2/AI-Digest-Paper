from __future__ import annotations
from langgraph.graph import StateGraph, END
from .state import GraphState
from .nodes.fetch import fetch_papers
from .nodes.summarize import summarize_topk
from .nodes.assemble import assemble_digest
from .nodes.persist import persist_run
from .nodes.filter import filter_candidates
from .nodes.rank import rank_papers

def build():
    """
    Build and compile the LangGraph workflow.

    MVP graph:
      FetchPapers -> SummarizeTopK -> AssembleDigest -> PersistRun -> END
    """
    g = StateGraph(GraphState)

    # Register nodes
    g.add_node("FetchPapers", fetch_papers)
    g.add_node("FilterCandidates", filter_candidates)
    g.add_node("SummarizeTopK", summarize_topk)
    g.add_node("AssembleDigest", assemble_digest)
    g.add_node("PersistRun", persist_run)
    g.add_node("RankPapers", rank_papers)
    # Entry point
    g.set_entry_point("FetchPapers")

    # Edges
    g.add_edge("FetchPapers", "FilterCandidates")
    g.add_edge("FilterCandidates", "RankPapers")
    g.add_edge("RankPapers", "SummarizeTopK")
    g.add_edge("SummarizeTopK", "AssembleDigest")
    g.add_edge("AssembleDigest", "PersistRun")
    g.add_edge("PersistRun", END)

    # Compile to executable graph
    return g.compile()
