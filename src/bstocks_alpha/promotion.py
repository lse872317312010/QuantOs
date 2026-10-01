"""Machine-readable research promotion gates for candidate strategies."""

from __future__ import annotations

import polars as pl

KEYS = ("horizon_s", "market_session", "preferred_side", "threshold_bps")


def research_promotion_gate(
    threshold_report: pl.DataFrame,
    walk_forward_summary: pl.DataFrame,
    *,
    min_selected_folds: int = 3,
    min_test_market_dates: int = 10,
    min_positive_oos_fold_rate: float = 0.60,
    min_mean_oos_daily_net_bps: float = 0.0,
) -> pl.DataFrame:
    """Combine TRAIN screening and repeated OOS evidence into explicit research states."""
    if min_selected_folds < 1:
        raise ValueError("min_selected_folds must be positive")
    if min_test_market_dates < 1:
        raise ValueError("min_test_market_dates must be positive")
    if not 0 <= min_positive_oos_fold_rate <= 1:
        raise ValueError("min_positive_oos_fold_rate must be between 0 and 1")

    required_threshold = {*KEYS, "stable_train_candidate"}
    missing_threshold = sorted(required_threshold - set(threshold_report.columns))
    if missing_threshold:
        raise ValueError(f"Promotion gate threshold input missing columns: {missing_threshold}")

    base = threshold_report.select(
        *KEYS,
        "stable_train_candidate",
        "train_market_dates",
        "train_mean_daily_net_bps",
        "train_fdr_q_value",
    ).unique(KEYS)

    if walk_forward_summary.is_empty():
        joined = base.with_columns(
            pl.lit(None, dtype=pl.Int64).alias("selected_folds"),
            pl.lit(None, dtype=pl.Int64).alias("test_market_dates"),
            pl.lit(None, dtype=pl.Float64).alias("mean_oos_daily_net_bps"),
            pl.lit(None, dtype=pl.Float64).alias("median_oos_daily_net_bps"),
            pl.lit(None, dtype=pl.Float64).alias("positive_oos_fold_rate"),
        )
    else:
        required_walk = {
            *KEYS,
            "selected_folds",
            "test_market_dates",
            "mean_oos_daily_net_bps",
            "median_oos_daily_net_bps",
            "positive_oos_fold_rate",
        }
        missing_walk = sorted(required_walk - set(walk_forward_summary.columns))
        if missing_walk:
            raise ValueError(f"Promotion gate walk-forward input missing columns: {missing_walk}")
        joined = base.join(walk_forward_summary, on=list(KEYS), how="left")

    return (
        joined.with_columns(
            pl.when(~pl.col("stable_train_candidate"))
            .then(pl.lit("REJECTED_TRAIN"))
            .when(pl.col("selected_folds").is_null())
            .then(pl.lit("INSUFFICIENT_WALK_FORWARD"))
            .when(
                (pl.col("selected_folds") < min_selected_folds)
                | (pl.col("test_market_dates") < min_test_market_dates)
            )
            .then(pl.lit("INSUFFICIENT_OOS_HISTORY"))
            .when(
                (pl.col("positive_oos_fold_rate") < min_positive_oos_fold_rate)
                | (pl.col("mean_oos_daily_net_bps") <= min_mean_oos_daily_net_bps)
            )
            .then(pl.lit("OOS_WEAK"))
            .otherwise(pl.lit("RESEARCH_CANDIDATE"))
            .alias("research_state"),
            pl.lit(min_selected_folds).alias("gate_min_selected_folds"),
            pl.lit(min_test_market_dates).alias("gate_min_test_market_dates"),
            pl.lit(min_positive_oos_fold_rate).alias("gate_min_positive_oos_fold_rate"),
            pl.lit(min_mean_oos_daily_net_bps).alias("gate_min_mean_oos_daily_net_bps"),
        )
        .sort(*KEYS)
    )
