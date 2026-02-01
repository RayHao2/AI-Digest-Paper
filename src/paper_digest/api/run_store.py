"""
Docstring for paper_digest.api.run_store:

A minimal database abstraction. It will craete run records, update run state, 
retrieve a single run, and list past runs  

"""

# src/paper_digest/api/run_store.py
from __future__ import annotations

import threading
from typing import Any, Dict, Optional


class RunStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: Dict[str, Dict[str, Any]] = {}

    def create(self, run_id: str, data: Dict[str, Any]) -> None:
        """Create a new run record."""
        with self._lock:
            self._runs[run_id] = dict(data)

    def update(self, run_id: str, data: Dict[str, Any]) -> None:
        """Patch fields of an existing run record."""
        with self._lock:
            if run_id not in self._runs:
                self._runs[run_id] = {}
            self._runs[run_id].update(data)

    def get(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            v = self._runs.get(run_id)
            return dict(v) if v else None

