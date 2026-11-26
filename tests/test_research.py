import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from bstocks_alpha.research import (
    analyze_file,
    forward_outcomes,
    label_us_equity_sessions,
    prepare_signals,
    summarize_forward_outcomes,
)

NY = ZoneInfo("America/New_York")


def epoch_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def raw_row(
    when: datetime,
    *,
    bid: float = 99.0,
    ask: float = 100.0,
    long_edge: float = 100.0,
    short_edge: float = -100.0,
    book_age_ms: int = 100,
    reference_receive_age_ms: int = 100,
) -> dict[str, object]:
    timestamp_ms = epoch_ms(when)
    return {
        "observed_timestamp_ms": timestamp_ms,
        "book_update_id": 42,
        "symbol": "SPYBUSDT",
        "bid": bid,
        "ask": ask,
        "mid": (bid + ask) / 2,
        "basis_bps": -100.0,
        "long_convergence_bps": long_edge,
        "short_convergence_bps": short_edge,
        "gross_convergence_edge_bps": max(long_edge, short_edge),
        "book_age_ms": book_age_ms,
        "reference_receive_age_ms": reference_receive_age_ms,
        "reference_lag_ms": 250,
    }


def test_session_labels_include_pre_regular_after_closed_and_holiday() -> None:
    frame = pl.DataFrame(
        [
            {"observed_timestamp_ms": epoch_ms(datetime(2026, 9, 30, 8, 0, tzinfo=NY))},
            {"observed_timestamp_ms": epoch_ms(datetime(2026, 9, 30, 10, 0, tzinfo=NY))},
            {"observed_timestamp_ms": epoch_ms(datetime(2026, 9, 30, 17, 0, tzinfo=NY))},
            {"observed_timestamp_ms": epoch_ms(datetime(2026, 9, 30, 21, 0, tzinfo=NY))},
            {"observed_timestamp_ms": epoch_ms(datetime(2026, 12, 25, 10, 0, tzinfo=NY))},
        ]
    )

    result = label_us_equity_sessions(frame)
    assert result["market_session"].to_list() == [
        "PRE",
        "REGULAR",
        "AFTER",
        "CLOSED",
        "CLOSED",
    ]


def test_prepare_signals_filters_stale_stream_events() -> None:
    rows = [
        raw_row(datetime(2026, 9, 30, 10, 0, tzinfo=NY)),
        raw_row(
            datetime(2026, 9, 30, 10, 0, 1, tzinfo=NY),
            book_age_ms=10_000,
        ),
    ]
    result = prepare_signals(pl.DataFrame(rows), max_event_age_ms=5_000)
    assert result.height == 1
    assert result["preferred_side"].to_list() == ["LONG"]
    assert result["freshness_bucket"].to_list() == ["0-1s"]
    assert result["market_session"].to_list() == ["REGULAR"]


def test_winter_evening_uses_local_calendar_when_utc_is_already_tomorrow():
    timestamp = epoch_ms(datetime(2026, 11, 2, 19, 30, tzinfo=NY))
    result = label_us_equity_sessions(pl.DataFrame({"observed_timestamp_ms": [timestamp]}))
    assert result["market_date"].to_list() == ["2026-11-02"]
    assert result["market_session"].to_list() == ["AFTER"]


def test_prepare_signals_requires_the_pair_to_be_known_at_its_recorded_entry():
    row = raw_row(datetime(2026, 9, 30, 10, 0, tzinfo=NY))
    when = row["observed_timestamp_ms"]
    rows = [
        dict(row, symbol="old-stream"),
        dict(row, symbol="old-rest", book_update_id=None),
        dict(row, symbol="new-rest", book_update_id=None, available_timestamp_ms=when),
        dict(row, symbol="late", available_timestamp_ms=when + 1),
        dict(row, symbol="future-reference", reference_lag_ms=-10),
    ]
    assert set(prepare_signals(pl.DataFrame(rows))["symbol"]) == {"old-stream", "new-rest"}


def test_forward_outcome_uses_executable_exit_side() -> None:
    start = datetime(2026, 9, 30, 10, 0, tzinfo=NY)
    rows = [
        raw_row(start, bid=99.0, ask=100.0),
        raw_row(
            start.replace(microsecond=0),
            bid=99.0,
            ask=100.0,
        ),
    ]
    rows[1]["observed_timestamp_ms"] = rows[0]["observed_timestamp_ms"] + 1_000
    rows[1]["bid"] = 101.0
    rows[1]["ask"] = 102.0
    rows[1]["mid"] = 101.5

    signals = prepare_signals(pl.DataFrame(rows), max_event_age_ms=5_000)
    outcomes = forward_outcomes(signals, horizons_s=(1,), max_match_lag_ms=0)
    first = outcomes.filter(
        pl.col("observed_timestamp_ms") == rows[0]["observed_timestamp_ms"]
    ).to_dicts()[0]

    assert first["preferred_side"] == "LONG"
    assert first["forward_match_lag_ms"] == 0
    assert first["forward_trade_return_bps"] == pytest.approx(100.0)


def test_summary_reports_matched_forward_returns() -> None:
    start = datetime(2026, 9, 30, 10, 0, tzinfo=NY)
    rows = [
        raw_row(start, bid=99.0, ask=100.0),
        raw_row(start, bid=101.0, ask=102.0),
    ]
    rows[1]["observed_timestamp_ms"] = rows[0]["observed_timestamp_ms"] + 1_000

    signals = prepare_signals(pl.DataFrame(rows))
    outcomes = forward_outcomes(signals, horizons_s=(1,), max_match_lag_ms=0)
    summary = summarize_forward_outcomes(outcomes)
    assert summary["matched"].sum() == 1


def test_analysis_excludes_a_delayed_exit_from_split_statistics(tmp_path) -> None:
    midnight = datetime(2026, 10, 1, tzinfo=NY)
    raw = pl.DataFrame([
        raw_row(midnight + timedelta(milliseconds=ms)) for ms in (-5000, -4000, -1500, 0, 1000)
    ])
    source = tmp_path / "basis.csv"
    raw.write_csv(source)
    target = tmp_path / "results"
    analyze_file(source, target, horizons_s=(1,), max_match_lag_ms=600, thresholds_bps=(5.0,))

    # The nominal target is 500 ms before midnight, but the first observed exit
    # is exactly midnight. Keep the outcome for audit and remove it from fitting.
    outcomes = pl.read_parquet(target / "forward_outcomes.parquet")
    purged = outcomes.filter(pl.col("sample") == "PURGED").row(0, named=True)
    assert purged["_future_timestamp_ms"] == epoch_ms(midnight)
    assert purged["forward_match_lag_ms"] == 500
    assert json.loads((target / "analysis_config.json").read_text())["holdout_purged_labels"] == 1
    assert pl.read_csv(target / "forward_summary.csv")["matched"].sum() == 3
    assert pl.read_csv(target / "holdout_summary.csv")["matched"].sum() == 2
    assert pl.read_csv(target / "daily_net_summary.csv")["matched_trades"].sum() == 2
    assert set(pl.read_csv(target / "bootstrap_ci.csv")["sample"]) == {"TRAIN", "TEST"}
    thresholds = pl.read_csv(target / "threshold_stability.csv").row(0, named=True)
    assert thresholds["train_matched_trades"] == thresholds["test_matched_trades"] == 1
    gate = pl.read_csv(target / "promotion_gate.csv").row(0, named=True)
    assert datetime.fromisoformat(gate["available_at"]) >= midnight + timedelta(seconds=1)


@pytest.mark.parametrize("conflicting", [False, True])
def test_forward_outcomes_rejects_ambiguous_same_symbol_timestamp(conflicting):
    start = datetime(2026, 9, 30, 10, 0, tzinfo=NY)
    exit_row = raw_row(start + timedelta(seconds=1), bid=101.0, ask=102.0)
    duplicate = dict(exit_row)
    if conflicting:
        duplicate.update(bid=95.0, ask=96.0, mid=95.5)
    for pair in ((exit_row, duplicate), (duplicate, exit_row)):
        signals = prepare_signals(pl.DataFrame([raw_row(start), *pair]))
        with pytest.raises(ValueError, match="Duplicate .* research keys"):
            forward_outcomes(signals, horizons_s=(1,), max_match_lag_ms=0)


def test_forward_outcomes_matches_only_same_symbol_with_shuffled_input():
    start = datetime(2026, 9, 30, 10, 0, tzinfo=NY)
    t0 = epoch_ms(start)
    rows = [
        raw_row(start, bid=99.0, ask=100.0),
        raw_row(start + timedelta(seconds=1), bid=101.0, ask=102.0),
        dict(raw_row(start, bid=199.0, ask=200.0), symbol="NVDABUSDT"),
        dict(
            raw_row(start + timedelta(milliseconds=1100), bid=196.0, ask=197.0),
            symbol="NVDABUSDT",
        ),
    ]
    for ordered in (rows, [rows[i] for i in (3, 1, 2, 0)]):
        signals = prepare_signals(pl.DataFrame(ordered))
        result = forward_outcomes(signals, horizons_s=(1,), max_match_lag_ms=100)
        first = {
            row["symbol"]: row
            for row in result.filter(pl.col("observed_timestamp_ms") == t0).to_dicts()
        }
        assert first["SPYBUSDT"]["_future_timestamp_ms"] == t0 + 1000
        assert first["SPYBUSDT"]["forward_trade_return_bps"] == pytest.approx(100.0)
        assert first["NVDABUSDT"]["_future_timestamp_ms"] == t0 + 1100
        assert first["NVDABUSDT"]["forward_trade_return_bps"] == pytest.approx(-200.0)
        unmatched = result.filter(pl.col("observed_timestamp_ms") != t0)
        assert unmatched["_future_timestamp_ms"].null_count() == 2
        assert unmatched["forward_trade_return_bps"].null_count() == 2
