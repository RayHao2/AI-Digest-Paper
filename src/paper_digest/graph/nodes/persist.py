from __future__ import annotations
from pathlib import Path
from datetime import datetime
from ..state import GraphState


def persist_run(state: GraphState) -> GraphState:
    """
    Persist digest output to disk. Later we'll also store 'seen' paper ids and summary JSON.
    """
    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    run_date = state.get("run_date") or datetime.now().strftime("%Y-%m-%d")
    safe_date = run_date.replace("/", "-")

    digest_md = state.get("digest_md", "")
    out_path = out_dir / f"digest_{safe_date}.md"
    out_path.write_text(digest_md, encoding="utf-8")

    state.setdefault("logs", []).append(f"PersistRun: wrote {out_path.as_posix()}")
    return state
