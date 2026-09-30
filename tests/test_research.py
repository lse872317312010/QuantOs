from datetime import datetime
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from bstocks_alpha.research import (
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
