from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from bstocks_alpha.promotion import research_promotion_gate
from bstocks_alpha.walkforward import summarize_walk_forward, walk_forward_threshold_report


def outcome(
    market_date: str,
    net_bps: float,
    *,
    edge_bps: float = 30.0,
) -> dict[str, object]:
    day = datetime.fromisoformat(market_date).replace(tzinfo=ZoneInfo("America/New_York"))
    return {
        "market_date": market_date,
        "sample": "IGNORED",
        "horizon_s": 5,
        "market_session": "REGULAR",
        "preferred_side": "LONG",
        "gross_convergence_edge_bps": edge_bps,
        "net_forward_trade_return_bps": net_bps,
        "_future_timestamp_ms": int((day + timedelta(hours=12)).timestamp() * 1000),
    }


def test_walk_forward_repeats_train_only_selection_into_later_test_dates() -> None:
    rows = []
    for day in range(1, 13):
        rows.append(outcome(f"2026-09-{day:02d}", 8.0 + day))

    report = walk_forward_threshold_report(
        pl.DataFrame(rows),
        thresholds_bps=(5.0, 10.0, 25.0),
        train_size_dates=6,
        test_size_dates=2,
        purged_size_dates=1,
        expand_train=False,
        min_train_dates=5,
        fdr_alpha=0.05,
    )

    assert report["fold"].n_unique() >= 2
    first = report.filter(pl.col("fold") == 1)
    assert first["train_start_date"][0] == "2026-09-01"
    assert first["train_end_date"][0] == "2026-09-06"
    assert first["test_start_date"][0] == "2026-09-08"
    assert first["test_end_date"][0] == "2026-09-09"
    assert first["stable_train_candidate"].to_list() == [True, True, True]


def test_walk_forward_returns_empty_when_history_is_too_short() -> None:
    frame = pl.DataFrame([outcome("2026-09-01", 5.0), outcome("2026-09-02", 6.0)])
    result = walk_forward_threshold_report(
        frame,
        train_size_dates=5,
        test_size_dates=2,
        purged_size_dates=1,
    )
    assert result.is_empty()


@pytest.mark.parametrize("gap", [0, 1])
def test_walk_forward_repurges_actual_exits_for_each_fold(gap: int) -> None:
    rows = [outcome(f"2026-09-{day:02d}", float(day)) for day in range(1, 10)]
    # The last TRAIN label ends on the first reserved date. A long TEST label
    # ends beyond this fold, but belongs to the training history of a later fold.
    rows[2]["_future_timestamp_ms"] = rows[3]["_future_timestamp_ms"]
    test_index = 3 + gap
    rows[test_index]["_future_timestamp_ms"] = rows[test_index + 2]["_future_timestamp_ms"]
    options = {
        "thresholds_bps": (5.0,),
        "train_size_dates": 3,
        "test_size_dates": 2,
        "purged_size_dates": gap,
        "min_train_dates": 2,
    }
    first = walk_forward_threshold_report(pl.DataFrame(rows), **options).row(0, named=True)
    assert first["train_matched_trades"] == 2
    assert first["train_mean_daily_net_bps"] == pytest.approx(1.5)
    assert first["test_matched_trades"] == 1
    assert first["fold_purged_train_labels"] == first["fold_purged_test_labels"] == 1
    changed = [dict(row) for row in rows]
    changed[2]["net_forward_trade_return_bps"] = 100_000.0
    changed[test_index]["net_forward_trade_return_bps"] = -100_000.0
    repeat = walk_forward_threshold_report(pl.DataFrame(changed), **options).row(0, named=True)
    assert repeat == first


def test_walk_forward_summary_uses_only_train_selected_candidates() -> None:
    report = pl.DataFrame(
        [
            {
                "fold": 1,
                "horizon_s": 5,
                "market_session": "REGULAR",
                "preferred_side": "LONG",
                "threshold_bps": 10.0,
                "stable_train_candidate": True,
                "test_market_dates": 2,
                "test_mean_daily_net_bps": 4.0,
            },
            {
                "fold": 2,
                "horizon_s": 5,
                "market_session": "REGULAR",
                "preferred_side": "LONG",
                "threshold_bps": 10.0,
                "stable_train_candidate": True,
                "test_market_dates": 2,
                "test_mean_daily_net_bps": -2.0,
            },
            {
                "fold": 3,
                "horizon_s": 5,
                "market_session": "REGULAR",
                "preferred_side": "LONG",
                "threshold_bps": 10.0,
                "stable_train_candidate": False,
                "test_market_dates": 2,
                "test_mean_daily_net_bps": 100.0,
            },
        ]
    )
    summary = summarize_walk_forward(report).to_dicts()[0]
    assert summary["selected_folds"] == 2
    assert summary["mean_oos_daily_net_bps"] == pytest.approx(1.0)
    assert summary["positive_oos_fold_rate"] == pytest.approx(0.5)


@pytest.mark.parametrize("completed", [1, 3])
def test_only_selected_folds_with_realized_test_labels_count_toward_promotion(completed):
    cell = {
        "horizon_s": 5, "market_session": "REGULAR", "preferred_side": "LONG", "threshold_bps": 5.0,
    }
    folds = pl.DataFrame([
        {
            **cell, "fold": i, "stable_train_candidate": True,
            "test_market_dates": 10 if i < completed else 0,
            "test_mean_daily_net_bps": 4.0 if i < completed else None,
        }
        for i in range(3)
    ])
    summary = summarize_walk_forward(folds)
    assert summary["train_selected_folds"].item() == 3
    assert summary["selected_folds"].item() == completed
    training = pl.DataFrame([{
        **cell, "stable_train_candidate": True, "train_market_dates": 20,
        "train_mean_daily_net_bps": 4.0, "train_fdr_q_value": 0.01,
    }])
    state = research_promotion_gate(training, summary)["research_state"].item()
    assert state == ("RESEARCH_CANDIDATE" if completed == 3 else "INSUFFICIENT_OOS_HISTORY")
