from dataclasses import replace

import pytest

from bstocks_alpha.dataset import append_snapshot_csv
from bstocks_alpha.snapshot import BasisObservation


def observation() -> BasisObservation:
    return BasisObservation(
        observed_at_utc="2026-09-30T00:00:00+00:00",
        observed_timestamp_ms=200,
        symbol="SPYBUSDT",
        base_asset="SPYB",
        inferred_underlying_ticker="SPY",
        bid=100.0,
        ask=100.1,
        mid=100.05,
        spread_bps=9.995,
        reference_price=100.0,
        reference_timestamp_ms=123,
        reference_lag_ms=77,
        basis_bps=5.0,
        long_convergence_bps=-9.99000999,
        short_convergence_bps=0.0,
        gross_convergence_edge_bps=0.0,
        external_calculation_id=2,
    )


def test_append_snapshot_csv(tmp_path) -> None:
    target = tmp_path / "basis.csv"
    assert append_snapshot_csv([observation()], target) == 1
    assert append_snapshot_csv([observation()], target) == 1
    lines = target.read_text().splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("observed_at_utc,observed_timestamp_ms,symbol")


def test_append_snapshot_csv_rejects_schema_mismatch(tmp_path) -> None:
    target = tmp_path / "basis.csv"
    target.write_text("old,header\n1,2\n")
    with pytest.raises(ValueError, match="schema mismatch"):
        append_snapshot_csv([observation()], target)


def test_append_to_old_stream_schema_preserves_provable_sample_time(tmp_path):
    from dataclasses import fields

    target = tmp_path / "old-stream.csv"
    sample = replace(observation(), book_update_id=19, available_timestamp_ms=200)
    old_columns = [field.name for field in fields(sample) if field.name != "available_timestamp_ms"]
    target.write_text(",".join(old_columns) + "\n")
    assert append_snapshot_csv([sample], target) == 1
    assert len(target.read_text().splitlines()[1].split(",")) == len(old_columns)
    with pytest.raises(ValueError, match="schema mismatch"):
        append_snapshot_csv([replace(sample, book_update_id=None)], target)
