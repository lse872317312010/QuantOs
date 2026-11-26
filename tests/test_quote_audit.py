import hashlib
import json
import subprocess
import sys

import polars as pl
import pytest

from bstocks_alpha.quote_audit import FORMAT, audit_directory


def quotes(keys, bids):
    return pl.DataFrame({
        "symbol": [symbol for symbol, _ in keys],
        "observed_timestamp_ms": [time for _, time in keys],
        "bid": bids, "ask": [102.0] * len(keys), "mid": [100.0] * len(keys),
        "basis_bps": [10.0] * len(keys),
    })


def test_retained_rows_group_within_symbol_and_count_once_per_key(tmp_path):
    frame = quotes(
        [("A", 1), ("B", 1), ("A", 1), ("A", 1), ("B", 2), ("B", 2), ("B", 3), ("B", 3)],
        [99.0, 99.0, 95.0, None, 99.0, 99.0, 99.0, float("nan")],
    )
    path = tmp_path / "signals.parquet"
    frame.write_parquet(path)
    before = path.read_bytes()
    result = audit_directory(tmp_path)
    assert result == {
        "status": "duplicate_keys", "sha256": hashlib.sha256(before).hexdigest(),
        "signal_rows": 8, "duplicate_keys": 3, "rows_in_duplicate_keys": 7, "surplus_rows": 4,
        "conflicting_quote_keys": 1, "equal_quote_keys": 1, "unclassified_quote_keys": 1,
    }
    assert path.read_bytes() == before
    frame.reverse().write_parquet(path)
    reversed_result = audit_directory(tmp_path)
    assert {k: v for k, v in result.items() if k != "sha256"} == {
        k: v for k, v in reversed_result.items() if k != "sha256"
    }


def test_legacy_signals_without_quote_fields_preserve_key_evidence(tmp_path):
    frame = quotes([("A", 1), ("A", 1), ("B", 1)], [10, 10, 10]).drop("basis_bps")
    frame.write_parquet(tmp_path / "signals.parquet")
    result = audit_directory(tmp_path)
    assert result["status"] == "duplicate_keys"
    assert result["duplicate_keys"] == result["unclassified_quote_keys"] == 1
    assert result["equal_quote_keys"] == result["conflicting_quote_keys"] == 0


@pytest.mark.parametrize(("transform", "reason"), [
    (lambda f: f.head(0), "empty_signals"),
    (lambda f: f.drop("symbol"), "missing_key"),
    (lambda f: f.with_columns(pl.lit(None, dtype=pl.Int64).alias("observed_timestamp_ms")), "invalid_key"),
    (lambda f: f.with_columns(pl.lit("  ").alias("symbol")), "invalid_key"),
    (lambda f: f.with_columns(pl.lit(1.5).alias("observed_timestamp_ms")), "invalid_key"),
    (lambda f: f.with_columns(pl.lit(1).alias("horizon_s")), "label_table"),
])
def test_incomplete_or_wrong_artifact_never_claims_zero_collisions(tmp_path, transform, reason):
    transform(quotes([("A", 1)], [99])).write_parquet(tmp_path / "signals.parquet")
    result = audit_directory(tmp_path)
    assert result["status"] == "unverified" and result["reason"] == reason
    assert len(result["sha256"]) == 64 and "duplicate_keys" not in result


def test_replacement_during_read_is_inconclusive(tmp_path, monkeypatch):
    frame = quotes([("A", 1)], [99])
    path = tmp_path / "signals.parquet"
    frame.write_parquet(path)
    original = pl.read_parquet

    def replace_after_read(*args, **kwargs):
        result = original(*args, **kwargs)
        replacement = tmp_path / "replacement.parquet"
        frame.write_parquet(replacement)
        replacement.replace(path)
        return result

    monkeypatch.setattr(pl, "read_parquet", replace_after_read)
    assert audit_directory(tmp_path) == {
        "status": "unverified", "sha256": None, "reason": "changed_during_read",
    }


def test_cli_keeps_input_order_and_unknown_overrides_collision_exit(tmp_path):
    valid, collision, missing = [tmp_path / name for name in ("unique", "duplicate", "absent")]
    valid.mkdir()
    collision.mkdir()
    frame = quotes([("A", 1), ("B", 1)], [10.0, 20.0])
    frame.write_parquet(valid / "signals.parquet")
    pl.concat([frame, frame.head(1)]).write_parquet(collision / "signals.parquet")

    def run(*dirs):
        proc = subprocess.run([sys.executable, "-m", "bstocks_alpha.quote_audit", *dirs],
                              capture_output=True, text=True, check=False)
        assert str(tmp_path) not in proc.stdout
        report = json.loads(proc.stdout)
        assert report["format"] == FORMAT
        return proc.returncode, report["batches"]

    status, batches = run(valid)
    assert status == 0 and batches[0]["duplicate_keys"] == 0
    assert run(collision, valid)[0] == 1
    status, batches = run(collision, missing, valid)
    assert status == 2
    assert [b["batch"] for b in batches] == [1, 2, 3]
    assert [b["status"] for b in batches] == ["duplicate_keys", "unverified", "unique_keys"]
    assert batches[1]["reason"] == "missing_signals" and not missing.exists()
    (valid / "signals.parquet").write_bytes(b"corrupt archive")
    assert audit_directory(valid)["reason"] == "invalid_parquet"
