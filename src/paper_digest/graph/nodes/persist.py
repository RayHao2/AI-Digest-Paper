from __future__ import annotations
from pathlib import Path
from datetime import datetime
from ..state import GraphState


def persist_run(state: GraphState) -> GraphState:
    run_id = state.get("run_id", "unknown_run")
    out_dir = Path(state.get("out_dir", "outputs")).resolve()

    run_dir = out_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    out_path = run_dir / "digest.md"
    out_path.write_text(state.get("digest_md", ""), encoding="utf-8")

    state.setdefault("logs", []).append(
        f"PersistRun: wrote {out_path}"
    )
    return state
