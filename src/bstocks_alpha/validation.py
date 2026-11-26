"""Cost sensitivity and chronological out-of-sample validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import floor, isfinite

import polars as pl

MATCHED_EXIT_MS = "_future_timestamp_ms"


@dataclass(frozen=True, slots=True)
class CostModel:
    """Simple additive bps cost model around already spread-crossing returns."""

    taker_fee_bps_per_side: float = 10.0
    slippage_bps_per_side: float = 0.0
    short_borrow_bps_per_day: float = 0.0

    def __post_init__(self) -> None:
        values = (
            self.taker_fee_bps_per_side,
            self.slippage_bps_per_side,
            self.short_borrow_bps_per_day,
        )
        if any(not isfinite(value) or value < 0 for value in values):
            raise ValueError("cost assumptions must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class HoldoutSplit:
    frame: pl.DataFrame
    cutoff_date: str | None
    train_dates: int
    test_dates: int


def _matched_holding_ms(outcomes: pl.DataFrame) -> pl.Expr:
    target_ms = pl.col("horizon_s") * 1_000
    has_lag = "forward_match_lag_ms" in outcomes.columns
    lag = pl.col("forward_match_lag_ms")
    if MATCHED_EXIT_MS in outcomes.columns and "observed_timestamp_ms" in outcomes.columns:
        duration = pl.col(MATCHED_EXIT_MS) - pl.col("observed_timestamp_ms")
        valid = duration >= target_ms
        if has_lag:
            valid &= lag.is_null() | (duration == target_ms + lag)
    elif has_lag:
        # Older exports retained the offset from the target to the matched quote.
        duration = target_ms + lag
        valid = lag >= 0
        if MATCHED_EXIT_MS in outcomes.columns:
            valid &= pl.col(MATCHED_EXIT_MS).is_not_null()
    else:
        return pl.lit(None, dtype=pl.Float64)
    return pl.when((target_ms > 0) & duration.is_finite() & valid).then(duration)


def apply_cost_model(outcomes: pl.DataFrame, model: CostModel) -> pl.DataFrame:
    """Subtract taker fees, additional slippage and prorated short borrow from gross return."""
    round_trip_fee_bps = 2.0 * model.taker_fee_bps_per_side
    round_trip_slippage_bps = 2.0 * model.slippage_bps_per_side

    short_borrow = pl.lit(0.0)
    if model.short_borrow_bps_per_day:
        short_borrow = _matched_holding_ms(outcomes) * (model.short_borrow_bps_per_day / 86_400_000)
    borrow_cost = (
        pl.when(pl.col("forward_trade_return_bps").is_null())
        .then(None)
        .when(pl.col("preferred_side") == "SHORT")
        .then(short_borrow)
        .otherwise(0.0)
        .alias("borrow_cost_bps")
    )

    return (
        outcomes.with_columns(
            pl.lit(round_trip_fee_bps).alias("round_trip_fee_bps"),
            pl.lit(round_trip_slippage_bps).alias("round_trip_slippage_bps"),
            borrow_cost,
        )
        .with_columns(
            (
                pl.col("round_trip_fee_bps")
                + pl.col("round_trip_slippage_bps")
                + pl.col("borrow_cost_bps")
            ).alias("total_cost_bps")
        )
        .with_columns(
            (pl.col("forward_trade_return_bps") - pl.col("total_cost_bps")).alias(
                "net_forward_trade_return_bps"
            )
        )
    )


def purge_overlapping_labels(
    tagged: pl.DataFrame, *, train_before: str, test_through: str,
) -> pl.DataFrame:
    """Keep the matched exit inside its window, retaining excluded rows for audit."""
    returns = [
        name for name in ("forward_trade_return_bps", "net_forward_trade_return_bps")
        if name in tagged.columns
    ]
    if not returns:
        return tagged  # Plain date partitions have no outcome labels.
    if MATCHED_EXIT_MS not in tagged.columns:
        raise ValueError(f"Missing {MATCHED_EXIT_MS}: rebuild labels from the original observations")
    scored = pl.any_horizontal(pl.col(name).is_not_null() for name in returns)
    if tagged.select((scored & pl.col(MATCHED_EXIT_MS).is_null()).any()).item():
        raise ValueError(f"A scored return is missing its observed exit ({MATCHED_EXIT_MS})")

    exit_date = (
        pl.from_epoch(pl.col(MATCHED_EXIT_MS), time_unit="ms")
        .dt.convert_time_zone("America/New_York")
        .dt.date()
    )
    crosses_train = (pl.col("sample") == "TRAIN") & (exit_date >= date.fromisoformat(train_before))
    crosses_test = (pl.col("sample") == "TEST") & (exit_date > date.fromisoformat(test_through))
    return tagged.with_columns(
        pl.when(crosses_train | crosses_test)
        .then(pl.lit("PURGED"))
        .otherwise(pl.col("sample"))
        .alias("sample")
    )


def chronological_holdout(
    outcomes: pl.DataFrame,
    *,
    test_fraction: float = 0.30,
) -> HoldoutSplit:
    """Split whole New York market dates chronologically; never randomize individual rows."""
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    if "market_date" not in outcomes.columns:
        raise ValueError("market_date is required for chronological holdout")

    dates = sorted(outcomes["market_date"].drop_nulls().unique().to_list())
    if len(dates) < 2:
        return HoldoutSplit(
            frame=outcomes.with_columns(pl.lit("UNSPLIT").alias("sample")),
            cutoff_date=None,
            train_dates=len(dates),
            test_dates=0,
        )

    train_date_count = floor(len(dates) * (1.0 - test_fraction))
    train_date_count = max(1, min(len(dates) - 1, train_date_count))
    cutoff_date = str(dates[train_date_count - 1])

    tagged = outcomes.with_columns(
        pl.when(pl.col("market_date").is_null())
        .then(pl.lit("UNSPLIT"))
        .when(pl.col("market_date") <= cutoff_date)
        .then(pl.lit("TRAIN"))
        .otherwise(pl.lit("TEST"))
        .alias("sample")
    )
    return HoldoutSplit(
        frame=purge_overlapping_labels(
            tagged, train_before=str(dates[train_date_count]), test_through=str(dates[-1]),
        ),
        cutoff_date=cutoff_date,
        train_dates=train_date_count,
        test_dates=len(dates) - train_date_count,
    )


def summarize_holdout(outcomes: pl.DataFrame) -> pl.DataFrame:
    """Compare gross and cost-adjusted outcomes between chronological train/test samples."""
    required = {"sample", "net_forward_trade_return_bps", "total_cost_bps"}
    missing = sorted(required - set(outcomes.columns))
    if missing:
        raise ValueError(f"Holdout summary missing required columns: {missing}")

    return (
        outcomes.filter(pl.col("sample") != "PURGED").group_by(
            "sample",
            "horizon_s",
            "market_session",
            "freshness_bucket",
            "edge_bucket",
            "preferred_side",
        )
        .agg(
            pl.len().alias("signals"),
            pl.col("net_forward_trade_return_bps").count().alias("matched"),
            pl.col("gross_convergence_edge_bps").mean().alias("mean_signal_edge_bps"),
            pl.col("total_cost_bps").mean().alias("mean_total_cost_bps"),
            pl.col("forward_trade_return_bps").mean().alias("mean_gross_forward_trade_bps"),
            pl.col("net_forward_trade_return_bps").mean().alias("mean_net_forward_trade_bps"),
            pl.col("net_forward_trade_return_bps")
            .median()
            .alias("median_net_forward_trade_bps"),
            (pl.col("net_forward_trade_return_bps") > 0).mean().alias("net_positive_rate"),
            pl.col("basis_convergence_bps").mean().alias("mean_basis_convergence_bps"),
        )
        .sort(
            "sample",
            "horizon_s",
            "market_session",
            "freshness_bucket",
            "edge_bucket",
            "preferred_side",
        )
    )
