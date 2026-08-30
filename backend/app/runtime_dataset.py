"""Ephemeral uploaded-dataset store used when the primary database is unavailable.

This store is intentionally process-local and demo-only. Production database behavior
is unchanged: when PostgreSQL is reachable it remains the source of truth.
"""
from threading import Lock
from typing import Any

_lock = Lock()
_rows: list[dict[str, Any]] = []
_batch_id: str | None = None


def set_dataset(rows: list[dict[str, Any]], batch_id: str) -> None:
    global _rows, _batch_id
    with _lock:
        _rows = [dict(row) for row in rows]
        _batch_id = batch_id


def get_dataset() -> tuple[str | None, list[dict[str, Any]]]:
    with _lock:
        return _batch_id, [dict(row) for row in _rows]


def clear_dataset() -> None:
    global _rows, _batch_id
    with _lock:
        _rows = []
        _batch_id = None
