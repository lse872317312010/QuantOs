"""Append-only research dataset writer."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from .snapshot import BasisObservation


def append_snapshot_csv(
    observations: Iterable[BasisObservation],
    path: str | Path,
) -> int:
    rows = [asdict(item) for item in observations]
    if not rows:
        return 0

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    exists = target.exists() and target.stat().st_size > 0
    fieldnames = list(rows[0].keys())

    if exists:
        with target.open("r", newline="", encoding="utf-8") as handle:
            existing_header = next(csv.reader(handle), [])
        # Older stream files can retain their schema when the book update ID
        # identifies a completed pair and its sample time is the availability.
        legacy_header = [name for name in fieldnames if name != "available_timestamp_ms"]
        if existing_header == legacy_header and all(
            row["book_update_id"] is not None and row["available_timestamp_ms"] == row["observed_timestamp_ms"]
            for row in rows
        ):
            fieldnames = legacy_header
            for row in rows:
                del row["available_timestamp_ms"]
        if existing_header != fieldnames:
            raise ValueError(
                f"CSV schema mismatch for {target}; use a new file or migrate the existing dataset"
            )

    with target.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)

    return len(rows)
