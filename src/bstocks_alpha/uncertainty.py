"""Date-clustered uncertainty estimates for bStocks research outcomes."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import polars as pl

BOOTSTRAP_GROUP_KEYS = (
    "sample",
    "horizon_s",
    "market_session",
    "edge_bucket",
    "preferred_side",
)


def daily_net_summary(outcomes: pl.DataFrame) -> pl.DataFrame:
    """Collapse high-frequency observations to market-date clusters before inference."""
    required = {
        "sample",
        "market_date",
        "horizon_s",
        "market_session",
        "edge_bucket",
        "preferred_side",
        "symbol",
        "net_forward_trade_return_bps",
        "gross_convergence_edge_bps",
    }
    missing = sorted(required - set(outcomes.columns))
    if missing:
        raise ValueError(f"Daily summary missing required columns: {missing}")

    return (
        outcomes.filter(pl.col("net_forward_trade_return_bps").is_not_null())
        .group_by(
            "sample",
            "market_date",
            "horizon_s",
            "market_session",
            "edge_bucket",
            "preferred_side",
        )
        .agg(
            pl.len().alias("matched_trades"),
            pl.col("symbol").n_unique().alias("symbols"),
            pl.col("net_forward_trade_return_bps").mean().alias("daily_mean_net_bps"),
            pl.col("net_forward_trade_return_bps").median().alias("daily_median_net_bps"),
            (pl.col("net_forward_trade_return_bps") > 0).mean().alias("daily_positive_rate"),
            pl.col("gross_convergence_edge_bps").mean().alias("daily_mean_signal_edge_bps"),
        )
        .sort(
            "sample",
            "market_date",
            "horizon_s",
            "market_session",
            "edge_bucket",
            "preferred_side",
        )
    )


def date_cluster_bootstrap(
    daily: pl.DataFrame,
    *,
    resamples: int = 2_000,
    confidence: float = 0.95,
    min_dates: int = 5,
    seed: int = 8_723,
) -> pl.DataFrame:
    """Bootstrap market-date means so intraday sampling frequency does not fake sample size."""
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if min_dates < 2:
        raise ValueError("min_dates must be at least 2")

    required = {*BOOTSTRAP_GROUP_KEYS, "market_date", "daily_mean_net_bps", "matched_trades"}
    missing = sorted(required - set(daily.columns))
    if missing:
        raise ValueError(f"Bootstrap input missing required columns: {missing}")

    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in daily.to_dicts():
        key = tuple(row[column] for column in BOOTSTRAP_GROUP_KEYS)
        grouped[key].append(row)

    alpha = (1.0 - confidence) / 2.0
    rows: list[dict[str, object]] = []

    ordered_groups = sorted(grouped.items(), key=lambda item: tuple(str(value) for value in item[0]))
    for group_index, (key, group_rows) in enumerate(ordered_groups):
        values = np.asarray(
            [float(row["daily_mean_net_bps"]) for row in group_rows],
            dtype=np.float64,
        )
        market_dates = len(values)
        matched_trades = sum(int(row["matched_trades"]) for row in group_rows)
        mean_daily = float(values.mean())
        median_daily = float(np.median(values))
        positive_day_rate = float((values > 0).mean())

        low: float | None = None
        high: float | None = None
        excludes_zero: bool | None = None
        status = "INSUFFICIENT_DATES"

        if market_dates >= min_dates:
            rng = np.random.default_rng(seed + group_index)
            sample_indices = rng.integers(
                0,
                market_dates,
                size=(resamples, market_dates),
            )
            bootstrap_means = values[sample_indices].mean(axis=1)
            low, high = (
                float(value)
                for value in np.quantile(bootstrap_means, [alpha, 1.0 - alpha])
            )
            excludes_zero = low > 0 or high < 0
            status = "OK"

        row = {
            column: value for column, value in zip(BOOTSTRAP_GROUP_KEYS, key, strict=True)
        }
        row.update(
            {
                "market_dates": market_dates,
                "matched_trades": matched_trades,
                "mean_daily_net_bps": mean_daily,
                "median_daily_net_bps": median_daily,
                "positive_day_rate": positive_day_rate,
                "confidence": confidence,
                "bootstrap_resamples": resamples,
                "ci_low_bps": low,
                "ci_high_bps": high,
                "ci_excludes_zero": excludes_zero,
                "status": status,
            }
        )
        rows.append(row)

    return pl.DataFrame(rows) if rows else pl.DataFrame()
