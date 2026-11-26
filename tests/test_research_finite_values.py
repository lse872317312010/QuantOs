from datetime import UTC, datetime

import polars as pl
import pytest

from bstocks_alpha.research import analyze_file, forward_outcomes, prepare_signals

T0 = int(datetime(2026, 7, 2, 14, 0, tzinfo=UTC).timestamp() * 1000)


def observation(offset_ms, **overrides):
    timestamp = T0 + offset_ms
    return {
        "symbol": "SYNTH", "observed_timestamp_ms": timestamp, "available_timestamp_ms": timestamp,
        "bid": 100.0, "ask": 101.0, "mid": 100.5, "basis_bps": -5.0,
        "long_convergence_bps": 8.0, "short_convergence_bps": -2.0,
        "gross_convergence_edge_bps": 8.0, "book_age_ms": 0, "reference_receive_age_ms": 0,
        "reference_lag_ms": 0, **overrides,
    }


def test_prepare_signals_requires_all_quote_and_edge_values_to_be_finite():
    columns = ["bid", "ask", "mid", "basis_bps", "long_convergence_bps",
               "short_convergence_bps", "gross_convergence_edge_bps"]
    rows = [observation(0, gross_convergence_edge_bps=0.0)]
    for column in columns:
        for value in (None, float("nan"), float("inf"), float("-inf")):
            rows.append(observation(len(rows), **{column: value}))

    signals = prepare_signals(pl.DataFrame(rows))
    assert signals["observed_timestamp_ms"].to_list() == [T0]
    assert signals["edge_bucket"].to_list() == ["<=0"]
    assert signals["basis_bps"].item() == -5.0


def test_analysis_uses_the_next_valid_exit_within_tolerance(tmp_path):
    source, output = tmp_path / "capture.csv", tmp_path / "run"
    rows = [
        observation(0),
        observation(1000, bid=float("inf"), ask=float("inf"), mid=float("inf")),
        observation(1050, gross_convergence_edge_bps=float("nan")),
        observation(1100, bid=103.0, ask=104.0, mid=103.5),
    ]
    pl.DataFrame(rows).write_csv(source)
    analyze_file(source, output, horizons_s=(1,), max_match_lag_ms=200)
    retained = pl.read_parquet(output / "signals.parquet")
    assert retained["observed_timestamp_ms"].to_list() == [T0, T0 + 1100]
    labels = pl.read_parquet(output / "forward_outcomes.parquet")
    assert labels["forward_match_lag_ms"].to_list() == [100, None]
    assert labels["forward_trade_return_bps"].to_list() == [
        pytest.approx((103 / 101 - 1) * 10_000), None,
    ]


def test_all_missing_csv_edge_produces_no_research_output(tmp_path):
    path, target = tmp_path / "blank.csv", tmp_path / "result"
    pl.DataFrame([observation(0, gross_convergence_edge_bps=None)]).write_csv(path)
    with pytest.raises(ValueError, match="No usable observations"):
        analyze_file(path, target)
    assert not target.exists()


def test_prepared_signals_reject_an_invalid_exit_before_matching():
    signals = prepare_signals(pl.DataFrame([observation(0), observation(1000)]))
    broken = signals.with_columns(pl.Series("ask", [101.0, float("nan")]))
    with pytest.raises(ValueError, match="finite"):
        forward_outcomes(broken, horizons_s=(1,))


def test_overflow_from_finite_prices_keeps_match_but_leaves_return_unscored():
    signals = prepare_signals(pl.DataFrame([
        observation(0, bid=1e-300, ask=1e-300, mid=1e-300),
        observation(1000, bid=1e300, ask=1e300, mid=1e300),
    ]))
    first = forward_outcomes(signals, horizons_s=(1,), max_match_lag_ms=0).row(0, named=True)
    assert first["forward_match_lag_ms"] == 0
    assert first["forward_trade_return_bps"] is None
    assert first["forward_mid_return_bps"] is None
    assert first["basis_convergence_bps"] == 0.0
