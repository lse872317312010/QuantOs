"""Append-only decision snapshot journal."""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from quantos.contracts import DecisionSnapshot


def _jsonable(
    value: Any,
    path: tuple[str | int, ...],
    nonfinite: list[dict[str, Any]],
) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return _jsonable(value.value, path, nonfinite)
    if isinstance(value, float) and not math.isfinite(value):
        kind = "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
        nonfinite.append({"path": list(path), "kind": kind})
        return None
    if isinstance(value, (tuple, list)):
        return [_jsonable(item, (*path, index), nonfinite) for index, item in enumerate(value)]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            key = str(key)
            if key in result:
                raise ValueError("duplicate journal key after string conversion")
            result[key] = _jsonable(item, (*path, key), nonfinite)
        return result
    return value


class DecisionJournal:
    """Persist point-in-time decision views for audit and later outcome review."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, snapshot: DecisionSnapshot) -> None:
        nonfinite: list[dict[str, Any]] = []
        payload = _jsonable(asdict(snapshot), (), nonfinite)
        if nonfinite:
            payload["nonfinite_values"] = nonfinite
        line = json.dumps(payload, sort_keys=True, allow_nan=False) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def entries(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        rows = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        return tuple(rows)
