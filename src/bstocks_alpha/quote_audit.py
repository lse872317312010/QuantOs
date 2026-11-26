"""Check quote-key collisions in the pre-label snapshots of archived research runs."""

import argparse
import hashlib
import json
import os
from pathlib import Path

import polars as pl

KEY = ["symbol", "observed_timestamp_ms"]
EXIT_FIELDS = ["bid", "ask", "mid", "basis_bps"]
FORMAT = "quantos.quote-key-audit.v1"


def _measure(frame: pl.DataFrame) -> dict:
    if frame.is_empty():
        return {"status": "unverified", "reason": "empty_signals"}
    schema = frame.schema
    if schema["symbol"] != pl.String or not schema["observed_timestamp_ms"].is_integer():
        return {"status": "unverified", "reason": "invalid_key"}
    valid_key = (
        (pl.col("symbol").str.strip_chars().str.len_chars() > 0)
        & (pl.col("observed_timestamp_ms") > 0)
    )
    if not frame.select(valid_key.fill_null(False).all()).item():
        return {"status": "unverified", "reason": "invalid_key"}

    comparable = all(
        name in schema and (schema[name].is_float() or schema[name].is_integer())
        for name in EXIT_FIELDS
    )
    aggregates = [pl.len().alias("rows")]
    if comparable:
        complete = pl.all_horizontal(pl.col(EXIT_FIELDS).is_finite()).fill_null(False)
        aggregates.extend([
            complete.all().alias("complete"),
            pl.struct(EXIT_FIELDS).filter(complete).n_unique().alias("variants"),
        ])
    duplicates = frame.group_by(KEY).agg(aggregates).filter(pl.col("rows") > 1)
    groups = duplicates.height
    rows = int(duplicates["rows"].cast(pl.UInt64).sum())
    conflicts = equal = 0
    if comparable:
        conflicts = duplicates.filter(pl.col("variants") > 1).height
        equal = duplicates.filter(pl.col("complete") & (pl.col("variants") == 1)).height
    return {
        "status": "duplicate_keys" if groups else "unique_keys",
        "signal_rows": frame.height,
        "duplicate_keys": groups,
        "rows_in_duplicate_keys": rows,
        "surplus_rows": rows - groups,
        "conflicting_quote_keys": conflicts,
        "equal_quote_keys": equal,
        "unclassified_quote_keys": groups - conflicts - equal,
    }


def _version(stat: os.stat_result) -> tuple[int, ...]:
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def audit_directory(directory: Path) -> dict:
    """Read only signals.parquet. Unknown inputs have no numeric evidence."""
    path = directory / "signals.parquet"
    unknown = {"status": "unverified", "sha256": None}
    try:
        with path.open("rb") as stream:
            before = _version(os.fstat(stream.fileno()))
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            stream.seek(0)
            try:
                schema = pl.read_parquet_schema(stream)
                if "horizon_s" in schema or "_future_timestamp_ms" in schema:
                    result = {"status": "unverified", "reason": "label_table"}
                elif any(name not in schema for name in KEY):
                    result = {"status": "unverified", "reason": "missing_key"}
                else:
                    stream.seek(0)
                    columns = [name for name in KEY + EXIT_FIELDS if name in schema]
                    result = _measure(pl.read_parquet(stream, columns=columns))
            except pl.exceptions.PolarsError:
                result = {"status": "unverified", "reason": "invalid_parquet"}
            if before != _version(os.fstat(stream.fileno())) or before != _version(path.stat()):
                return {**unknown, "reason": "changed_during_read"}
            return {**result, "sha256": digest}
    except (FileNotFoundError, NotADirectoryError):
        return {**unknown, "reason": "missing_signals"}
    except OSError:
        return {**unknown, "reason": "unreadable"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path, help="Archived bstocks-analyze run directories")
    args = parser.parse_args()
    batches = [
        {"batch": index, **audit_directory(directory)}
        for index, directory in enumerate(args.directories, start=1)
    ]
    print(json.dumps({"format": FORMAT, "batches": batches}, indent=2))
    if any(batch["status"] == "unverified" for batch in batches):
        raise SystemExit(2)
    if any(batch["status"] == "duplicate_keys" for batch in batches):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
