from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

def get_gemini_api_key() -> str:
    # repo root = .../AI-Digest-Paper
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env", override=True)

    key = (os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing. Put it in .env or env var.")
    return key
