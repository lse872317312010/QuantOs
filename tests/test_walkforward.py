from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from bstocks_alpha.walkforward import summarize_walk_forward, walk_forward_threshold_report


def outcome(
    market_date: str,
    net_bps: float,
    *,
    edge_bps: float = 30.0,
) -> dict[str, object]:
    end = datetime.combine(date.fromisoformat(market_date), time(12), ZoneInfo("America/New_York"))
    return {
        "market_date": market_date,
        "label_end_timestamp_ms": int(end.timestamp()) * 1000,
        "sample": "IGNORED",
        "horizon_s": 5,
        "market_session": "REGULAR",
        "preferred_side": "LONG",
        "gross_convergence_edge_bps": edge_bps,
        "net_forward_trade_return_bps": net_bps,
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


def test_each_fold_checks_realized_exits_even_across_the_purge_gap() -> None:
    rows = [outcome(f"2026-09-{day:02d}", float(day)) for day in range(1, 11)]
    # Fold 1 trains on 1-3 and tests on 5-6. The last TRAIN and TEST exits cross their bounds.
    rows[2]["label_end_timestamp_ms"] = rows[4]["label_end_timestamp_ms"]
    rows[5]["label_end_timestamp_ms"] = rows[6]["label_end_timestamp_ms"]
    report = walk_forward_threshold_report(
        pl.DataFrame(rows), thresholds_bps=(5,), train_size_dates=3, test_size_dates=2,
        purged_size_dates=1, min_train_dates=2,
    )
    first = report.filter(pl.col("fold") == 1).row(0, named=True)
    assert first["purged_label_rows"] == 2
    assert first["train_matched_trades"] == 2
    assert first["test_matched_trades"] == 1
    # A previously excluded label can be known when a later fold opens.
    second = report.filter(pl.col("fold") == 2).row(0, named=True)
    assert second["train_matched_trades"] == 5


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
