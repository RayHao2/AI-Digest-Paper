from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict


# Data Types 

class Paper(TypedDict, total=False):
    """
    Normalized representation of a paper, regardless of source.
    Keep this small for MVP; we can extend later.
    """
    paper_id: str              # Stable identifier (e.g., arXiv ID). Used for deduplication and tracing.
    source: str                # "arxiv", "pwc", etc.
    title: str
    authors: List[str]
    abstract: str
    url: str
    published_at: str          # ISO date string
    updated_at: str            # ISO date string
    categories: List[str]

    intro_text: str
    summary_text: str           # abstract text in the website, not acutal LLM summaries
    pdf_url: str                
    content_status: str         # Error message if full-text extraction fails
    content_error: str          # Error message if full-text extraction fails


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
    tags: List[str]             # LLM-generated topical tags
    url: str
    status: str                # "ok" | "failed"
    error: str                 # present if failed


# -----------------------------
# Graph-wide state
# -----------------------------

class GraphState(TypedDict, total=False):
    # Run context
    run_date: str
    topics: List[str]       # user input topics
    top_k: int              # numebr of paper to summarize
    max_results: int        # max paper fetched from source before ranking

    # Pipeline payloads
    raw_items: List[Dict[str, Any]]     # Raw records from source APIs before normalization
    papers: List[Paper]                 # Normalized Paper objects
    candidates: List[Paper]             # Filtered papers eligible for ranking
    ranked: List[Paper]                 # Papers sorted by relevance score (e.g., BM25)
    summaries: List[PaperSummary]
    digest_md: str

    # Diagnostics
    errors: List[str]               # pipelin-level erros
    logs: List[str]                 # human-readable exectution trace 
    rank_scores: List[float]        # optoinal rank score algined with `ranked` ppaer

    # Full-text extraction config
    fulltext_ready: List[Paper]     # Papers that successfully passed full-text extraction
    pdf_head_pages: int             # Number of pages extracted from the beginning of PDFs
    pdf_tail_pages: int             # Number of pages extracted from the end of PDFs
    pdf_fetch_limit: int            # Maximum number of PDFs to fetch in a run
    section_max_chars: int          # Character cap per extracted section
    pdf_polite_delay_s: float       # Delay between PDF fetches to avoid rate limiting
    # LLM model to use 
    llm_model: str

    # output check
    run_id: str
    out_dir: str 



