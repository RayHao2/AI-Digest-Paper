from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict


# Data Types 

class Paper(TypedDict, total=False):
    """
    Normalized representation of a paper, regardless of source.
    Keep this small for MVP; we can extend later.
    """
    paper_id: str              # stable id (e.g., arXiv id). used for dedupe
    source: str                # "arxiv", "pwc", etc.
    title: str
    authors: List[str]
    abstract: str
    url: str
    published_at: str          # ISO date string
    updated_at: str            # ISO date string
    categories: List[str]

    intro_text: str
    summary_text: str
    pdf_url: str
    content_status: str
    content_error: str


class PaperSummary(TypedDict, total=False):
    """
    Structured summary output (LLM later).
    """
    paper_id: str
    title: str
    one_liner: str
    key_contributions: List[str]
    methods: List[str]
    limitations: List[str]
    why_it_matters: str
    tags: List[str]
    url: str
    status: str                # "ok" | "failed"
    error: str                 # present if failed


# -----------------------------
# Graph-wide state
# -----------------------------

class GraphState(TypedDict, total=False):
    # Run context
    run_date: str
    topics: List[str]
    top_k: int
    max_results: int

    # Pipeline payloads
    raw_items: List[Dict[str, Any]]
    papers: List[Paper]
    candidates: List[Paper]
    ranked: List[Paper]
    summaries: List[PaperSummary]
    digest_md: str

    # Diagnostics
    errors: List[str]
    logs: List[str]
    rank_scores: List[float]

    fulltext_ready: List[Paper]
    pdf_head_pages: int
    pdf_tail_pages: int
    pdf_fetch_limit: int
    section_max_chars: int
    pdf_polite_delay_s: float
    # LLM model to use 
    llm_model: str

    # output check
    run_id: str
    out_dir: str 



