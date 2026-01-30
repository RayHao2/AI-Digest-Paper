from __future__ import annotations
from typing import List
from ..state import GraphState, PaperSummary

def assemble_digest(state: GraphState) -> GraphState:
    run_date = state.get("run_date", "")
    summaries: List[PaperSummary] = state.get("summaries", []) or []

    lines: List[str] = []
    lines.append(f"# AI Paper Digest ({run_date})\n")

    for i, s in enumerate(summaries, start=1):
        title = s.get("title", "Untitled")
        url = s.get("url", "")
        status = s.get("status", "ok")

        lines.append(f"## {i}. {title}")
        if url:
            lines.append(f"- Link: {url}")

        if status != "ok":
            lines.append(f"- Status: **failed**")
            lines.append(f"- Error: {s.get('error','')}")
            lines.append("")
            continue

        tags = s.get("tags", []) or []
        if tags:
            lines.append(f"- Tags: {', '.join(tags)}")

        one = (s.get("one_liner", "") or "").strip()
        if one:
            lines.append(f"- One-liner: {one}")

        why = (s.get("why_it_matters", "") or "").strip()
        if why:
            lines.append(f"- Why it matters: {why}")

        # Optional sections
        def add_bullets(label: str, items: List[str]):
            items = [x.strip() for x in (items or []) if x and x.strip()]
            if items:
                lines.append(f"- {label}:")
                for it in items:
                    lines.append(f"  - {it}")

        add_bullets("Key contributions", s.get("key_contributions", []))
        add_bullets("Methods", s.get("methods", []))
        add_bullets("Limitations", s.get("limitations", []))

        lines.append("")

    state["digest_md"] = "\n".join(lines).strip() + "\n"
    state.setdefault("logs", []).append(
        f"AssembleDigest: assembled digest with {len(summaries)} items."
    )
    return state
