from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List

from google import genai

from ..state import GraphState, Paper, PaperSummary
from ..schemas import SummarySchema
import random
import re
from paper_digest.config import get_gemini_api_key


_TRANSIENT_HTTP = {429, 500, 503}


def _extract_http_status(ex: Exception) -> int | None:
    """
    Best-effort: extract HTTP status code from common exception shapes/messages.
    Works even if we don't have a typed exception class.
    """
    # common attrs in google / requests style errors
    for attr in ("status_code", "code", "status"):
        val = getattr(ex, attr, None)
        if isinstance(val, int):
            return val

    msg = str(ex)
    m = re.search(r"\b(429|500|503)\b", msg)
    return int(m.group(1)) if m else None


def _is_transient(ex: Exception) -> bool:
    code = _extract_http_status(ex)
    if code in _TRANSIENT_HTTP:
        return True

    # extra safety: match typical quota/transient phrases
    low = str(ex).lower()
    if "quota" in low or "rate" in low or "exhaust" in low or "temporarily" in low:
        return True

    return False


def _sleep_backoff(attempt: int, base_s: float = 1.0, cap_s: float = 8.0) -> None:
    """
    attempt is 1-based. Exponential backoff: base * 2^(attempt-1), with jitter.
    attempt=1 -> ~1s, attempt=2 -> ~2s, attempt=3 -> ~4s ...
    """
    exp = min(cap_s, base_s * (2 ** (attempt - 1)))
    jitter = exp * (0.75 + 0.5 * random.random())  # 0.75x .. 1.25x
    time.sleep(jitter)


def _paper_context(p: Paper) -> str:
    title = (p.get("title") or "").strip()
    abstract = (p.get("abstract") or "").strip()
    intro = (p.get("intro_text") or "").strip()
    concl = (p.get("summary_text") or "").strip()

    if intro or concl:
        return (
            f"TITLE:\n{title}\n\n"
            f"INTRODUCTION (EXTRACTED):\n{intro}\n\n"
            f"CONCLUSION/SUMMARY (EXTRACTED):\n{concl}\n"
        )
    return f"TITLE:\n{title}\n\nABSTRACT:\n{abstract}\n"


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False,
                    indent=2), encoding="utf-8")


def summarize_topk(state: GraphState) -> GraphState:
    model = str(state.get("llm_model", "gemini-2.5-flash"))
    top_k = int(state.get("top_k", 5))
    topics = state.get("topics", []) or []

    ranked: List[Paper] = state.get("ranked", []) or state.get("papers", [])
    chosen = ranked[: min(len(ranked), top_k)]

    out_dir = Path(state.get("out_dir", "outputs")).resolve()
    run_dir = out_dir

    if not chosen:
        state["summaries"] = []
        state.setdefault("logs", []).append(
            "SummarizeTopK(Gemini): no papers to summarize.")
        return state

    system_instruction = (
        "You are an AI research assistant. "
        "Return factual, concise summaries. "
        "If content is insufficient, say so in limitations."
    )

    interest_line = f"User interests: {', '.join(topics)}\n\n" if topics else ""

    summaries: List[PaperSummary] = []
    ok = 0

    for idx, p in enumerate(chosen, start=1):
        paper_id = p.get("paper_id", "")
        url = p.get("url", "")
        title = p.get("title", "")

        # Per-paper artifact paths
        safe_id = paper_id.replace(
            "/", "_").replace(":", "_") or f"paper_{idx}"
        prompt_path = run_dir / "summaries" / f"{idx:02d}_{safe_id}_prompt.txt"
        raw_path = run_dir / "summaries" / f"{idx:02d}_{safe_id}_raw.txt"
        parsed_path = run_dir / "summaries" / \
            f"{idx:02d}_{safe_id}_parsed.json"

        context = _paper_context(p)

        prompt = (f"""
            {interest_line}Return ONLY valid JSON with the following schema:
            {{
            "paper_id": string,
            "title": string,
            "one_liner": string,
            "key_contributions": string[],
            "methods": string[],
            "limitations": string[],
            "why_it_matters": string,
            "tags": string[],
            "url": string,
            "status": "ok" | "failed",
            "error": string
            }}

            paper_id: {paper_id}
            url: {url}

            Content:
            {context}
        """)

        def _get_client() -> genai.Client:
            return genai.Client(api_key=get_gemini_api_key())

        client = _get_client()
        # Save prompt always
        _write_text(prompt_path, prompt)
        max_tries = 1
        last_err: Exception | None = None

        for attempt in range(1, max_tries + 1):
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "system_instruction": system_instruction,
                        "response_mime_type": "application/json",
                    },
                )

                raw_text = (resp.text or "").strip()
                _write_text(raw_path, raw_text)

                # <-- if this fails, treat as retryable once/twice
                data = json.loads(raw_text)

                # Fill defaults from metadata
                data.setdefault("paper_id", paper_id)
                data.setdefault("title", title)
                data.setdefault("url", url)
                data.setdefault("tags", p.get("categories", []) or [])
                data.setdefault("status", "ok")

                validated = SummarySchema(**data).model_dump()
                _write_json(parsed_path, validated)
                summaries.append(validated)  # type: ignore[arg-type]
                ok += 1
                last_err = None
                break

            except json.JSONDecodeError as ex:
                last_err = ex
                if attempt < max_tries:
                    _sleep_backoff(attempt)
                    continue
                break

            except Exception as ex:
                last_err = ex
                if attempt < max_tries and _is_transient(ex):
                    _sleep_backoff(attempt)
                    continue
                break

        if last_err is not None:
            failed = {
                "paper_id": paper_id,
                "title": title,
                "url": url,
                "status": "failed",
                "error": str(last_err),
                "tags": p.get("categories", []) or [],
                "one_liner": "",
                "key_contributions": [],
                "methods": [],
                "limitations": [],
                "why_it_matters": "",
            }
            _write_json(parsed_path, failed)
            summaries.append(failed)

    state["summaries"] = summaries
    state.setdefault("logs", []).append(
        f"SummarizeTopK(Gemini): produced {ok}/{len(chosen)} summaries using model='{model}'. "
        f"Artifacts in: {run_dir / 'summaries'}"
    )
    return state
