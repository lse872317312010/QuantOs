"""Append-only decision snapshot journal."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from quantos.contracts import DecisionSnapshot


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


class DecisionJournal:
    """Persist point-in-time decision views for audit and later outcome review."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, snapshot: DecisionSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = _jsonable(asdict(snapshot))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def entries(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        rows = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        return tuple(rows)
