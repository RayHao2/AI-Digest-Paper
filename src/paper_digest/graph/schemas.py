from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class SummarySchema(BaseModel):
    paper_id: str
    title: str
    one_liner: str
    key_contributions: List[str] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    why_it_matters: str
    tags: List[str] = Field(default_factory=list)
    url: str
    status: Literal["ok", "failed"] = "ok"
    error: Optional[str] = None
