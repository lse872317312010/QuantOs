from datetime import datetime
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from bstocks_alpha.research import forward_outcomes, label_us_equity_sessions
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
            "observed_timestamp_ms": [1_000, 1_000],
            "_future_timestamp_ms": [61_000, 86_401_000],
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


def test_short_borrow_follows_the_matched_exit_and_skips_unfilled_rows() -> None:
    signals = pl.DataFrame({
        "observed_timestamp_ms": [1_000, 3_500],
        "symbol": ["EXAMPLE"] * 2, "preferred_side": ["SHORT"] * 2,
        "bid": [100.0, 98.0], "ask": [101.0, 99.0],
        "mid": [100.5, 98.5], "basis_bps": [5.0, 0.0],
    })
    labels = forward_outcomes(signals, horizons_s=(1,), max_match_lag_ms=1_500)
    priced = apply_cost_model(labels, CostModel(0.0, 0.0, 864.0))
    assert priced["borrow_cost_bps"].to_list() == [pytest.approx(0.025), None]
    assert priced["total_cost_bps"].to_list() == [pytest.approx(0.025), None]
    assert priced["net_forward_trade_return_bps"][0] == pytest.approx(100.0 - 0.025)


def test_legacy_match_lag_recovers_duration_and_rejects_unverified_short_costs() -> None:
    labels = pl.DataFrame({
        "preferred_side": ["SHORT", "SHORT", "SHORT", "LONG"],
        "horizon_s": [1] * 4, "forward_match_lag_ms": [1_500, None, -1, None],
        "forward_trade_return_bps": [2.0] * 4,
    })
    model = CostModel(0.0, 0.0, 864.0)
    assert apply_cost_model(labels, model)["borrow_cost_bps"].to_list() == [
        pytest.approx(0.025), None, None, 0.0,
    ]
    no_timing = labels.drop("forward_match_lag_ms")
    assert apply_cost_model(no_timing, model)["net_forward_trade_return_bps"].to_list() == [
        None, None, None, 2.0,
    ]
    assert apply_cost_model(no_timing, CostModel(0, 0, 0))["borrow_cost_bps"].to_list() == [0.0] * 4


def test_recorded_exit_cannot_precede_target_or_disagree_with_match_lag() -> None:
    labels = pl.DataFrame({
        "preferred_side": ["SHORT"] * 4, "horizon_s": [1] * 4,
        "observed_timestamp_ms": [1_000] * 4, "_future_timestamp_ms": [1_999, 2_001, None, 2_001],
        "forward_match_lag_ms": [None, 2, 1, 1], "forward_trade_return_bps": [4.0] * 4,
    })
    costs = apply_cost_model(labels, CostModel(0.0, 0.0, 864.0))["borrow_cost_bps"].to_list()
    assert costs == [None, None, None, pytest.approx(0.01001)]


@pytest.mark.parametrize("rate", [float("nan"), float("inf")])
def test_non_finite_borrow_rate_is_rejected(rate: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        CostModel(short_borrow_bps_per_day=rate)


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


def test_holdout_uses_the_observed_exit_across_dst_midnight() -> None:
    # November 1 is a 25-hour New York date. The TEST date starts at 05:00 UTC.
    boundary = epoch_ms(datetime(2026, 11, 2, tzinfo=NY))
    outcomes = pl.DataFrame(
        {
            "market_date": ["2026-11-01"] * 4 + ["2026-11-02"],
            "_future_timestamp_ms": [boundary - 1, boundary, boundary + 1, None, boundary + 1000],
            "net_forward_trade_return_bps": [5.0, 99.0, 100.0, None, 2.0],
        }
    )
    split = chronological_holdout(outcomes, test_fraction=0.5)
    assert split.frame["sample"].to_list() == ["TRAIN", "PURGED", "PURGED", "TRAIN", "TEST"]
    assert split.frame.height == outcomes.height


def test_holdout_rejects_a_scored_label_without_a_verifiable_exit() -> None:
    frame = pl.DataFrame(
        {"market_date": ["2026-09-01", "2026-09-02"], "net_forward_trade_return_bps": [5.0, 2.0]}
    )
    with pytest.raises(ValueError, match="_future_timestamp_ms"):
        chronological_holdout(frame)
    with pytest.raises(ValueError, match="_future_timestamp_ms"):
        chronological_holdout(
            frame.with_columns(pl.lit(None, dtype=pl.Int64).alias("_future_timestamp_ms"))
        )


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
