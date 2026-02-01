"""
Docstring for paper_digest.api.models

The formal contract between:
    - Client <-> API
    - API <-> storage
    - Storage <-> Frontend 
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional



class RunRequest(BaseModel):
    topics: List[str] = Field(default_factory=list)
    top_k: int = 5
    max_results: int = 20
    llm_model: Optional[str] = None
    out_dir: str = "outputs"


class RunResponse(BaseModel):
    run_id: str
    run_date: str
    digest_md: str
    summaries: List[Dict[str, Any]] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


RunStatus = Literal["queued", "running", "done", "failed"]
class RunRecord(BaseModel):
    run_id: str
    run_date: str
    status: RunStatus
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    request: Dict[str, Any] = Field(default_factory=dict)

    # Results (present when done)
    digest_md: Optional[str] = None
    summaries: Optional[List[Dict[str, Any]]] = None
    logs: Optional[List[str]] = None
    errors: Optional[List[str]] = None

    # Failure
    error: Optional[str] = None