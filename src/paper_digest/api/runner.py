"""
Docstring for paper_digest.api.run_store:

The only palce where the LangGraph is atually exected. It will makrs run as running,
build the grpah, invoke it, capture outputs, marks run as done or failed 

"""

from __future__ import annotations

import time
from typing import Any, Dict

from paper_digest.graph.build_graph import build
from .run_store import RunStore


def run_pipeline(run_id: str, request: Dict[str, Any], store: RunStore) -> None:
    """
    Runs your LangGraph pipeline synchronously, updating run status in RunStore.
    Called by a background task.
    """
    store.update(run_id, {"status": "running", "started_at": time.time()})

    try:
        g = build()

        # GraphState is TypedDict, so a plain dict is fine:
        state_in = {
            "topics": request.get("topics", []),
            "top_k": int(request.get("top_k", 5)),
            "max_results": int(request.get("max_results", 20)),
            "llm_model": request.get("llm_model"),   # your summarize node reads this
            "out_dir": request.get("out_dir", "outputs"),
        }

        out = g.invoke(state_in)

        store.update(
            run_id,
            {
                "status": "done",
                "finished_at": time.time(),
                "digest_md": out.get("digest_md", ""),
                "summaries": out.get("summaries", []),
                "logs": out.get("logs", []),
                "errors": out.get("errors", []),
            },
        )

    except Exception as ex:
        store.update(
            run_id,
            {
                "status": "failed",
                "finished_at": time.time(),
                "error": str(ex),
            },
        )
