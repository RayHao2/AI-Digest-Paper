"""
Public Interface for the system.

This API:
- validates input
- creates a run_id
- stores "queued" run metadata
- starts background runner that executes LangGraph (in runner.py)
- exposes endpoints to check status + fetch results
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from paper_digest.api.models import RunRequest, RunResponse
from paper_digest.api.run_store import RunStore
from paper_digest.api.runner import run_pipeline

load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI(title="AI Paper Digest Agent", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten later
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Single store instance for the app process
    store = RunStore()

    # Health Endpoint
    @app.get("/health")
    def health():
        return {"ok": True}

    # Run Endpoint: start a new paper-digest run (async)
    @app.post("/run")
    def run(req: RunRequest, background: BackgroundTasks):
        run_id = datetime.now().strftime("%Y%m%d") + "_" + uuid4().hex[:8]
        run_date = datetime.now().strftime("%Y-%m-%d")

        request_dict: Dict[str, Any] = req.model_dump()

        # Create initial run record
        store.create(
            run_id,
            {
                "run_id": run_id,
                "run_date": run_date,
                "status": "queued",
                "request": request_dict,
            },
        )

        # Kick off pipeline asynchronously
        background.add_task(run_pipeline, run_id, request_dict, store)

        return {"run_id": run_id, "status": "queued"}

    # Fetch the current status + results of a run
    @app.get("/runs/{run_id}")
    def get_run(run_id: str):
        run = store.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="run_id not found")
        return run

    return app


app = create_app()
