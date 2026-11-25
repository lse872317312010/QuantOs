from datetime import datetime
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from bstocks_alpha.research import label_us_equity_sessions
from bstocks_alpha.validation import (
    CostModel,
    apply_cost_model,
    chronological_holdout,
    summarize_holdout,
)

NY = ZoneInfo("America/New_York")


def epoch_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def test_market_date_uses_new_york_calendar_date() -> None:
    frame = pl.DataFrame(
        {
            "observed_timestamp_ms": [
                epoch_ms(datetime(2026, 10, 1, 0, 30, tzinfo=ZoneInfo("UTC")))
            ]
        }
    )
    result = label_us_equity_sessions(frame)
    assert result["market_date"].to_list() == ["2026-09-30"]
    assert result["market_session"].to_list() == ["CLOSED"]


def test_cost_model_subtracts_round_trip_costs_and_short_borrow() -> None:
    outcomes = pl.DataFrame(
        {
            "preferred_side": ["LONG", "SHORT"],
            "horizon_s": [60, 86_400],
            "forward_trade_return_bps": [50.0, 50.0],
        }
    )
    result = apply_cost_model(
        outcomes,
        CostModel(
            taker_fee_bps_per_side=10.0,
            slippage_bps_per_side=2.0,
            short_borrow_bps_per_day=5.0,
        ),
    )

    rows = result.to_dicts()
    assert rows[0]["total_cost_bps"] == pytest.approx(24.0)
    assert rows[0]["net_forward_trade_return_bps"] == pytest.approx(26.0)
    assert rows[1]["borrow_cost_bps"] == pytest.approx(5.0)
    assert rows[1]["total_cost_bps"] == pytest.approx(29.0)
    assert rows[1]["net_forward_trade_return_bps"] == pytest.approx(21.0)


def test_chronological_holdout_splits_whole_market_dates() -> None:
    outcomes = pl.DataFrame(
        {
            "market_date": [
                "2026-09-28",
                "2026-09-29",
                "2026-09-30",
                "2026-10-01",
            ],
            "symbol": ["SPYBUSDT"] * 4,
        }
    )
    split = chronological_holdout(outcomes, test_fraction=0.25)
    assert split.cutoff_date == "2026-09-30"
    assert split.train_dates == 3
    assert split.test_dates == 1
    assert split.frame["sample"].to_list() == ["TRAIN", "TRAIN", "TRAIN", "TEST"]


def test_chronological_holdout_marks_single_day_unsplit() -> None:
    outcomes = pl.DataFrame({"market_date": ["2026-09-30"], "symbol": ["SPYBUSDT"]})
    split = chronological_holdout(outcomes)
    assert split.cutoff_date is None
    assert split.frame["sample"].to_list() == ["UNSPLIT"]


@pytest.mark.parametrize("column", ["label_end_timestamp_ms", "_future_timestamp_ms"])
def test_holdout_checks_actual_exit_at_new_york_midnight_and_keeps_missing_labels(column) -> None:
    start = epoch_ms(datetime(2026, 11, 1, tzinfo=NY))
    after = epoch_ms(datetime(2026, 11, 2, tzinfo=NY))  # 25-hour fall-back date
    frame = pl.DataFrame({
        "market_date": ["2026-10-31"] * 4 + ["2026-11-01"] * 2,
        column: [start - 1, start, start + 1, None, after - 1, after],
        "net_forward_trade_return_bps": [1, 2, 3, None, 4, 5],
    })
    split = chronological_holdout(frame)
    assert split.frame["sample"].to_list() == ["TRAIN", "PURGED", "PURGED", "TRAIN", "TEST", "PURGED"]
    assert split.frame["label_end_timestamp_ms"].to_list() == frame[column].to_list()


def test_holdout_refuses_returns_with_unknown_endpoints() -> None:
    frame = pl.DataFrame({
        "market_date": ["2026-10-01", "2026-10-02"],
        "net_forward_trade_return_bps": [1.0, None],
    })
    with pytest.raises(ValueError, match="label_end_timestamp_ms"):
        chronological_holdout(frame)
    with pytest.raises(ValueError, match="matched return"):
        chronological_holdout(frame.with_columns(pl.lit(None).alias("label_end_timestamp_ms")))


def test_holdout_summary_uses_net_returns() -> None:
    outcomes = pl.DataFrame(
        {
            "sample": ["TRAIN", "TEST"],
            "horizon_s": [5, 5],
            "market_session": ["REGULAR", "REGULAR"],
            "freshness_bucket": ["0-1s", "0-1s"],
            "edge_bucket": [">25", ">25"],
            "preferred_side": ["LONG", "LONG"],
            "gross_convergence_edge_bps": [40.0, 40.0],
            "total_cost_bps": [20.0, 20.0],
            "forward_trade_return_bps": [30.0, 10.0],
            "net_forward_trade_return_bps": [10.0, -10.0],
            "basis_convergence_bps": [20.0, 5.0],
        }
    )
    summary = summarize_holdout(outcomes)
    assert summary.height == 2
    test_row = summary.filter(pl.col("sample") == "TEST").to_dicts()[0]
    assert test_row["mean_net_forward_trade_bps"] == pytest.approx(-10.0)
    assert test_row["net_positive_rate"] == pytest.approx(0.0)
