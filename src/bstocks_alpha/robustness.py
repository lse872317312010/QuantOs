"""Train-only threshold stability and multiple-testing controls."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import polars as pl
from scipy.stats import false_discovery_control, ttest_1samp

GROUP_KEYS = ("horizon_s", "market_session", "preferred_side")


def threshold_stability_report(
    outcomes: pl.DataFrame,
    *,
    thresholds_bps: tuple[float, ...] = (5.0, 10.0, 15.0, 25.0, 50.0),
    min_train_dates: int = 5,
    fdr_alpha: float = 0.05,
) -> pl.DataFrame:
    """Sweep edge thresholds without using TEST data for candidate selection."""
    thresholds = tuple(sorted({float(value) for value in thresholds_bps}))
    if not thresholds or any(value <= 0 for value in thresholds):
        raise ValueError("thresholds_bps must contain positive values")
    if min_train_dates < 2:
        raise ValueError("min_train_dates must be at least 2")
    if not 0 < fdr_alpha < 1:
        raise ValueError("fdr_alpha must be between 0 and 1")

    required = {
        "sample",
        "market_date",
        "horizon_s",
        "market_session",
        "preferred_side",
        "gross_convergence_edge_bps",
        "net_forward_trade_return_bps",
    }
    missing = sorted(required - set(outcomes.columns))
    if missing:
        raise ValueError(f"Threshold report missing required columns: {missing}")

    daily_frames: list[pl.DataFrame] = []
    for threshold in thresholds:
        daily = (
            outcomes.filter(
                (pl.col("gross_convergence_edge_bps") >= threshold)
                & pl.col("net_forward_trade_return_bps").is_not_null()
                & pl.col("market_date").is_not_null()
            )
            .group_by("sample", "market_date", *GROUP_KEYS)
            .agg(
                pl.len().alias("matched_trades"),
                pl.col("net_forward_trade_return_bps").mean().alias("daily_mean_net_bps"),
            )
            .with_columns(pl.lit(threshold).alias("threshold_bps"))
        )
        if not daily.is_empty():
            daily_frames.append(daily)

    if not daily_frames:
        return pl.DataFrame()

    daily_all = pl.concat(daily_frames, how="vertical_relaxed")
    grouped_daily: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in daily_all.to_dicts():
        key = (
            row["sample"],
            row["horizon_s"],
            row["market_session"],
            row["preferred_side"],
            row["threshold_bps"],
        )
        grouped_daily[key].append(row)

    summaries: dict[tuple[object, ...], dict[str, object]] = {}
    train_p_values: dict[tuple[object, ...], float] = {}

    for key, rows in grouped_daily.items():
        sample, horizon_s, session, side, threshold = key
        values = np.asarray([float(row["daily_mean_net_bps"]) for row in rows], dtype=np.float64)
        candidate_key = (horizon_s, session, side, threshold)
        prefix = str(sample).lower()
        summary = summaries.setdefault(
            candidate_key,
            {
                "horizon_s": horizon_s,
                "market_session": session,
                "preferred_side": side,
                "threshold_bps": float(threshold),
                "train_market_dates": 0,
                "train_matched_trades": 0,
                "train_mean_daily_net_bps": None,
                "train_median_daily_net_bps": None,
                "train_positive_day_rate": None,
                "train_p_value": None,
                "train_fdr_q_value": None,
                "test_market_dates": 0,
                "test_matched_trades": 0,
                "test_mean_daily_net_bps": None,
                "test_median_daily_net_bps": None,
                "test_positive_day_rate": None,
            },
        )
        summary.update(
            {
                f"{prefix}_market_dates": len(values),
                f"{prefix}_matched_trades": sum(int(row["matched_trades"]) for row in rows),
                f"{prefix}_mean_daily_net_bps": float(values.mean()),
                f"{prefix}_median_daily_net_bps": float(np.median(values)),
                f"{prefix}_positive_day_rate": float((values > 0).mean()),
            }
        )

        if sample == "TRAIN" and len(values) >= min_train_dates:
            result = ttest_1samp(values, popmean=0.0, alternative="greater")
            p_value = float(result.pvalue)
            if np.isfinite(p_value):
                train_p_values[candidate_key] = p_value

    keys_with_p = list(train_p_values)
    if keys_with_p:
        adjusted = false_discovery_control(
            np.asarray([train_p_values[key] for key in keys_with_p], dtype=np.float64),
            method="bh",
        )
        for key, q_value in zip(keys_with_p, adjusted, strict=True):
            summaries[key]["train_p_value"] = train_p_values[key]
            summaries[key]["train_fdr_q_value"] = float(q_value)

    rows = []
    pass_by_family: dict[tuple[object, ...], dict[float, bool]] = defaultdict(dict)
    for key, summary in summaries.items():
        q_value = summary.get("train_fdr_q_value")
        mean_net = summary.get("train_mean_daily_net_bps")
        train_pass = (
            q_value is not None
            and mean_net is not None
            and float(q_value) <= fdr_alpha
            and float(mean_net) > 0
        )
        summary["train_fdr_pass"] = train_pass
        family = key[:3]
        pass_by_family[family][float(key[3])] = train_pass

    for key, summary in summaries.items():
        family = key[:3]
        threshold = float(key[3])
        position = thresholds.index(threshold)
        neighbors = []
        if position > 0:
            neighbors.append(thresholds[position - 1])
        if position + 1 < len(thresholds):
            neighbors.append(thresholds[position + 1])
        adjacent_passes = sum(bool(pass_by_family[family].get(value, False)) for value in neighbors)
        summary["adjacent_train_passes"] = adjacent_passes
        summary["stable_train_candidate"] = bool(summary["train_fdr_pass"]) and adjacent_passes > 0
        summary["fdr_alpha"] = fdr_alpha
        summary["min_train_dates"] = min_train_dates
        rows.append(summary)

    return pl.DataFrame(rows).sort(*GROUP_KEYS, "threshold_bps")
