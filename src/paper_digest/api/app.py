from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from paper_digest.graph.build_graph import build
from paper_digest.api.models import RunRequest, RunResponse


def create_app() -> FastAPI:
    app = FastAPI(title="AI Paper Digest Agent", version="0.1.0")

    # Allow your future web UI to call the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten later
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    graph = build()

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.post("/run", response_model=RunResponse)
    def run(req: RunRequest):
        run_id = datetime.now().strftime("%Y%m%d") + "_" + uuid4().hex[:8]
        run_date = datetime.now().strftime("%Y-%m-%d")

        state = {
            "run_date": run_date,
            "topics": req.topics,
            "top_k": req.top_k,
            "max_results": req.max_results,
            "out_dir": req.out_dir,
            "run_id": run_id,   
            "errors": [],
            "logs": [],
        }
        if req.llm_model:
            state["llm_model"] = req.llm_model

        result = graph.invoke(state)

        return RunResponse(
            run_id=run_id,
            run_date=run_date,
            digest_md=result.get("digest_md", ""),
            summaries=result.get("summaries", []) or [],
            logs=result.get("logs", []) or [],
            errors=result.get("errors", []) or [],
        )

    return app


app = create_app()
