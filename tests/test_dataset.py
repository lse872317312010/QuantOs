from bstocks_alpha.dataset import append_snapshot_csv
from bstocks_alpha.snapshot import BasisObservation


def test_append_snapshot_csv(tmp_path) -> None:
    observation = BasisObservation(
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
    target = tmp_path / "basis.csv"
    assert append_snapshot_csv([observation], target) == 1
    assert append_snapshot_csv([observation], target) == 1
    lines = target.read_text().splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("observed_at_utc,observed_timestamp_ms,symbol")
