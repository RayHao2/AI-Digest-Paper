from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class RunRequest(BaseModel):
    topics: List[str] = Field(default_factory=list)
    top_k: int = 5
    max_results: int = 20

    # optional knobs
    llm_model: Optional[str] = None
    out_dir: str = "outputs"


class RunResponse(BaseModel):
    run_id: str
    run_date: str
    digest_md: str
    summaries: List[Dict[str, Any]] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
