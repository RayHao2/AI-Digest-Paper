from __future__ import annotations

from datetime import datetime
from typing import List

from ..state import GraphState, PaperSummary


def assemble_digest(state: GraphState) -> GraphState:
    """
    Assemble the final Markdown digest from summaries.
    """
    run_date = state.get("run_date") or datetime.now().strftime("%Y-%m-%d")
    summaries: List[PaperSummary] = state.get("summaries", [])

    lines: List[str] = []
    lines.append(f"# AI Paper Digest ({run_date})")
    lines.append("")

    if not summaries:
        lines.append("No new papers found.")
        lines.append("")
        state["digest_md"] = "\n".join(lines)
        state.setdefault("logs", []).append("AssembleDigest: no summaries; produced empty digest.")
        return state

    for i, s in enumerate(summaries, start=1):
        title = s.get("title", "Untitled")
        url = s.get("url", "")
        one_liner = s.get("one_liner", "")
        why = s.get("why_it_matters", "")
        tags = s.get("tags", [])

        lines.append(f"## {i}. {title}")
        if url:
            lines.append(f"- Link: {url}")
        if tags:
            lines.append(f"- Tags: {', '.join(tags)}")
        if one_liner:
            lines.append(f"- One-liner: {one_liner}")
        if why:
            lines.append(f"- Why it matters: {why}")
        lines.append("")

    state["digest_md"] = "\n".join(lines)
    state.setdefault("logs", []).append(f"AssembleDigest: assembled digest with {len(summaries)} items.")
    return state
