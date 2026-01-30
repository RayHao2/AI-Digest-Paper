from __future__ import annotations

import re
import time
from typing import List, Optional, Tuple

import requests
import fitz  # PyMuPDF

from ..state import GraphState, Paper


_HEADING_RE = re.compile(r"^\s*(\d+(\.\d+)*)\s+([A-Z][A-Za-z0-9\-\s]{2,})\s*$")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]+")


def _get_pdf_url(p: Paper) -> str:
    """Prefer p['pdf_url'], else derive from arXiv abs url."""
    pdf_url = (p.get("pdf_url") or "").strip()
    if pdf_url:
        return pdf_url

    url = (p.get("url") or "").strip()
    if "/abs/" in url:
        return url.replace("/abs/", "/pdf/") + ".pdf"

    pid = (p.get("paper_id") or "").strip()
    if "/abs/" in pid:
        return pid.replace("/abs/", "/pdf/") + ".pdf"

    return ""


def _extract_pdf_text_windows(pdf_bytes: bytes, head_pages: int, tail_pages: int) -> Tuple[List[str], List[str]]:
    """
    Extract per-page text for:
      - head window: first `head_pages`
      - tail window: last `tail_pages`
    Returns (head_pages_text, tail_pages_text)
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n = len(doc)

    head_n = max(0, min(head_pages, n))
    tail_n = max(0, min(tail_pages, n))

    head_out: List[str] = []
    for i in range(head_n):
        head_out.append(doc.load_page(i).get_text("text") or "")

    tail_out: List[str] = []
    if tail_n > 0:
        start = max(0, n - tail_n)
        for i in range(start, n):
            tail_out.append(doc.load_page(i).get_text("text") or "")

    doc.close()
    return head_out, tail_out


def _find_section_ranges(pages_text: List[str]) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """
    Find intro / conclusion headings within the given window.
    Returns line indices: (intro_i, intro_end, concl_i, concl_end)
    """
    all_text = "\n".join(pages_text)
    lines = all_text.splitlines()

    headings: List[Tuple[int, str]] = []
    for i, line in enumerate(lines):
        l = line.strip()
        if not l:
            continue

        low = l.lower()
        if low in {"introduction", "conclusion", "conclusions", "summary", "discussion", "abstract", "references"}:
            headings.append((i, low))
            continue

        m = _HEADING_RE.match(l)
        if m:
            title = m.group(3).strip().lower()
            headings.append((i, title))

    def first_heading(names: List[str]) -> Optional[int]:
        for idx, title in headings:
            if any(n in title for n in names):
                return idx
        return None

    def next_heading_after(start: int) -> Optional[int]:
        for idx, _ in headings:
            if idx > start:
                return idx
        return None

    intro_i = first_heading(["introduction"])
    concl_i = first_heading(["conclusion", "conclusions", "summary", "discussion"])

    intro_end = next_heading_after(intro_i) if intro_i is not None else None
    concl_end = next_heading_after(concl_i) if concl_i is not None else None

    ref_i = first_heading(["references", "bibliography"])
    if concl_i is not None and concl_end is None and ref_i is not None and ref_i > concl_i:
        concl_end = ref_i

    return intro_i, intro_end, concl_i, concl_end


def _slice_lines(lines: List[str], start: Optional[int], end: Optional[int], max_chars: int) -> str:
    if start is None:
        return ""
    if end is None:
        end = len(lines)
    chunk = "\n".join(lines[start:end]).strip()
    return chunk[:max_chars] if len(chunk) > max_chars else chunk


def _fallback_intro(lines: List[str], max_chars: int) -> str:
    out: List[str] = []
    for ln in lines[:1500]:
        if _WORD_RE.search(ln):
            out.append(ln)
        if len("\n".join(out)) >= max_chars:
            break
    return "\n".join(out)[:max_chars].strip()


def _fallback_summary(lines: List[str], max_chars: int) -> str:
    tail = lines[-1200:] if len(lines) > 1200 else lines
    out = [ln for ln in tail if _WORD_RE.search(ln)]
    return "\n".join(out)[-max_chars:].strip()


def fetch_full_text(state: GraphState) -> GraphState:
    """
    Download PDFs for top-ranked papers and extract:
      - intro_text from head pages
      - summary_text from tail pages

    Writes:
      state["fulltext_ready"] = List[Paper] enriched with intro_text/summary_text
    """
    ranked: List[Paper] = state.get("ranked", []) or state.get("papers", [])
    top_k = int(state.get("top_k", 5))

    pdf_fetch_limit = int(state.get("pdf_fetch_limit", top_k))
    head_pages = int(state.get("pdf_head_pages", 8))
    tail_pages = int(state.get("pdf_tail_pages", 4))
    max_chars_each = int(state.get("section_max_chars", 60_000))
    polite_delay = float(state.get("pdf_polite_delay_s", 0.5))

    targets = ranked[: min(len(ranked), pdf_fetch_limit)]

    session = requests.Session()
    session.headers.update({"User-Agent": "paper-digest-agent/0.1"})

    ok = 0
    for p in targets:
        pdf_url = _get_pdf_url(p)
        p["pdf_url"] = pdf_url

        if not pdf_url:
            p["content_status"] = "failed"
            p["content_error"] = "No pdf_url found."
            continue

        try:
            r = session.get(pdf_url, timeout=35)
            r.raise_for_status()

            head_pages_text, tail_pages_text = _extract_pdf_text_windows(
                r.content, head_pages=head_pages, tail_pages=tail_pages
            )

            # Intro from head window
            head_lines = "\n".join(head_pages_text).splitlines()
            intro_i, intro_end, _, _ = _find_section_ranges(head_pages_text)
            intro_text = _slice_lines(head_lines, intro_i, intro_end, max_chars_each)
            if not intro_text:
                intro_text = _fallback_intro(head_lines, max_chars_each)

            # Summary from tail window
            tail_lines = "\n".join(tail_pages_text).splitlines()
            _, _, concl_i, concl_end = _find_section_ranges(tail_pages_text)
            summary_text = _slice_lines(tail_lines, concl_i, concl_end, max_chars_each)
            if not summary_text:
                summary_text = _fallback_summary(tail_lines, max_chars_each)

            p["intro_text"] = intro_text
            p["summary_text"] = summary_text
            p["content_status"] = "ok"
            ok += 1

        except Exception as ex:
            p["content_status"] = "failed"
            p["content_error"] = str(ex)

        if polite_delay > 0:
            time.sleep(polite_delay)

    state["fulltext_ready"] = targets
    state.setdefault("logs", []).append(
        f"FetchFullText(Head+Tail): enriched {ok}/{len(targets)} papers "
        f"(head_pages={head_pages}, tail_pages={tail_pages}, section_chars<={max_chars_each})."
    )

    # Output full text for manual inspection

    # from pathlib import Path

    # dump_dir = Path("outputs").resolve()
    # dump_dir.mkdir(parents=True, exist_ok=True)

    # dump_path = dump_dir / f"fulltext_review_{state.get('run_date','run')}.md"

    # lines = []
    # lines.append(f"# Full Text Review ({state.get('run_date','')})\n")

    # for i, p in enumerate(targets, start=1):
    #     lines.append(f"## {i}. {p.get('title','')}")
    #     lines.append(f"- URL: {p.get('url','')}")
    #     lines.append(f"- PDF: {p.get('pdf_url','')}")
    #     lines.append(f"- Status: {p.get('content_status','')}")
    #     if p.get("content_error"):
    #         lines.append(f"- Error: `{p['content_error']}`")

    #     lines.append("\n### Introduction (extracted)\n")
    #     lines.append("```text")
    #     lines.append((p.get("intro_text") or "(empty)")[:8000])
    #     lines.append("```")

    #     lines.append("\n### Conclusion / Summary (extracted)\n")
    #     lines.append("```text")
    #     lines.append((p.get("summary_text") or "(empty)")[:8000])
    #     lines.append("```")

    #     lines.append("\n---\n")

    # dump_path.write_text("\n".join(lines), encoding="utf-8")

    # state.setdefault("logs", []).append(
    #     f"FullTextReview: wrote {dump_path}"
    # )

    return state
