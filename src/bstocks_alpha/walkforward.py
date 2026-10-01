"""Repeated chronological out-of-sample validation using skfolio WalkForward."""

from __future__ import annotations

import numpy as np
import polars as pl
from skfolio.model_selection import WalkForward

from .robustness import threshold_stability_report


def walk_forward_threshold_report(
    outcomes: pl.DataFrame,
    *,
    thresholds_bps: tuple[float, ...] = (5.0, 10.0, 15.0, 25.0, 50.0),
    train_size_dates: int = 20,
    test_size_dates: int = 5,
    purged_size_dates: int = 1,
    expand_train: bool = True,
    min_train_dates: int = 5,
    fdr_alpha: float = 0.05,
) -> pl.DataFrame:
    """Repeat TRAIN-only threshold screening across chronological folds."""
    if train_size_dates < 2:
        raise ValueError("train_size_dates must be at least 2")
    if test_size_dates < 1:
        raise ValueError("test_size_dates must be positive")
    if purged_size_dates < 0:
        raise ValueError("purged_size_dates must be non-negative")
    if "market_date" not in outcomes.columns:
        raise ValueError("market_date is required for walk-forward validation")

    dates = sorted(str(value) for value in outcomes["market_date"].drop_nulls().unique().to_list())
    required_dates = train_size_dates + purged_size_dates + test_size_dates
    if len(dates) < required_dates:
        return pl.DataFrame()

    splitter = WalkForward(
        train_size=train_size_dates,
        test_size=test_size_dates,
        purged_size=purged_size_dates,
        expand_train=expand_train,
    )
    X = np.arange(len(dates), dtype=np.int64).reshape(-1, 1)
    fold_frames: list[pl.DataFrame] = []

    for fold, (train_idx, test_idx) in enumerate(splitter.split(X), start=1):
        train_dates = [dates[int(index)] for index in train_idx]
        test_dates = [dates[int(index)] for index in test_idx]
        if not train_dates or not test_dates:
            continue

        fold_frame = (
            outcomes.filter(pl.col("market_date").is_in(train_dates + test_dates))
            .with_columns(
                pl.when(pl.col("market_date").is_in(train_dates))
                .then(pl.lit("TRAIN"))
                .otherwise(pl.lit("TEST"))
                .alias("sample")
            )
        )
        report = threshold_stability_report(
            fold_frame,
            thresholds_bps=thresholds_bps,
            min_train_dates=min_train_dates,
            fdr_alpha=fdr_alpha,
        )
        if report.is_empty():
            continue

        report = report.with_columns(
            pl.lit(fold).alias("fold"),
            pl.lit(train_dates[0]).alias("train_start_date"),
            pl.lit(train_dates[-1]).alias("train_end_date"),
            pl.lit(test_dates[0]).alias("test_start_date"),
            pl.lit(test_dates[-1]).alias("test_end_date"),
            pl.lit(len(train_dates)).alias("fold_train_dates"),
            pl.lit(len(test_dates)).alias("fold_test_dates"),
            pl.lit(purged_size_dates).alias("purged_size_dates"),
            pl.lit(expand_train).alias("expand_train"),
        )
        fold_frames.append(report)

    if not fold_frames:
        return pl.DataFrame()
    return pl.concat(fold_frames, how="diagonal_relaxed").sort(
        "fold",
        "horizon_s",
        "market_session",
        "preferred_side",
        "threshold_bps",
    )


def summarize_walk_forward(report: pl.DataFrame) -> pl.DataFrame:
    """Summarize only fold decisions made from TRAIN information."""
    if report.is_empty():
        return pl.DataFrame()

    required = {
        "fold",
        "horizon_s",
        "market_session",
        "preferred_side",
        "threshold_bps",
        "stable_train_candidate",
        "test_market_dates",
        "test_mean_daily_net_bps",
    }
    missing = sorted(required - set(report.columns))
    if missing:
        raise ValueError(f"Walk-forward summary missing required columns: {missing}")

    selected = report.filter(pl.col("stable_train_candidate"))
    if selected.is_empty():
        return pl.DataFrame()

    return (
        selected.group_by(
            "horizon_s",
            "market_session",
            "preferred_side",
            "threshold_bps",
        )
        .agg(
            pl.col("fold").n_unique().alias("selected_folds"),
            pl.col("test_market_dates").sum().alias("test_market_dates"),
            pl.col("test_mean_daily_net_bps")
            .drop_nulls()
            .mean()
            .alias("mean_oos_daily_net_bps"),
            pl.col("test_mean_daily_net_bps")
            .drop_nulls()
            .median()
            .alias("median_oos_daily_net_bps"),
            (pl.col("test_mean_daily_net_bps").drop_nulls() > 0)
            .mean()
            .alias("positive_oos_fold_rate"),
        )
        .sort(
            "horizon_s",
            "market_session",
            "preferred_side",
            "threshold_bps",
        )
    )
