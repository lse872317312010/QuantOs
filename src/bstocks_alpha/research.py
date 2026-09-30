"""Offline forward-return research for collected bStocks basis observations."""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import polars as pl

NY = ZoneInfo("America/New_York")
REQUIRED_COLUMNS = {
    "observed_timestamp_ms",
    "symbol",
    "bid",
    "ask",
    "mid",
    "basis_bps",
    "long_convergence_bps",
    "short_convergence_bps",
    "gross_convergence_edge_bps",
    "book_age_ms",
    "reference_receive_age_ms",
    "reference_lag_ms",
}


def _require_columns(frame: pl.DataFrame, required: set[str] = REQUIRED_COLUMNS) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")


def _to_epoch_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _session_windows(start: date, end: date) -> pl.DataFrame:
    """Build XNYS regular/pre/after-market boundaries in epoch milliseconds."""
    calendar = xcals.get_calendar(
        "XNYS",
        start=(start - timedelta(days=7)).isoformat(),
        end=(end + timedelta(days=7)).isoformat(),
    )
    sessions = calendar.sessions_in_range(start.isoformat(), end.isoformat())
    rows: list[dict[str, object]] = []

    for session in sessions:
        open_utc = calendar.session_open(session).to_pydatetime().astimezone(UTC)
        close_utc = calendar.session_close(session).to_pydatetime().astimezone(UTC)
        local_date = open_utc.astimezone(NY).date()
        pre_open_utc = datetime.combine(local_date, time(4, 0), tzinfo=NY).astimezone(UTC)
        after_close_utc = datetime.combine(local_date, time(20, 0), tzinfo=NY).astimezone(UTC)

        rows.append(
            {
                "session_date": local_date.isoformat(),
                "pre_open_ms": _to_epoch_ms(pre_open_utc),
                "open_ms": _to_epoch_ms(open_utc),
                "close_ms": _to_epoch_ms(close_utc),
                "after_close_ms": _to_epoch_ms(after_close_utc),
            }
        )

    return pl.DataFrame(
        rows,
        schema={
            "session_date": pl.String,
            "pre_open_ms": pl.Int64,
            "open_ms": pl.Int64,
            "close_ms": pl.Int64,
            "after_close_ms": pl.Int64,
        },
    )


def label_us_equity_sessions(frame: pl.DataFrame) -> pl.DataFrame:
    """Label PRE / REGULAR / AFTER / CLOSED using the XNYS exchange calendar."""
    if frame.is_empty():
        return frame.with_columns(
            pl.lit(None, dtype=pl.String).alias("session_date"),
            pl.lit(None, dtype=pl.String).alias("market_session"),
        )

    minimum_ms = int(frame["observed_timestamp_ms"].min())
    maximum_ms = int(frame["observed_timestamp_ms"].max())
    start = datetime.fromtimestamp(minimum_ms / 1000, tz=UTC).date()
    end = datetime.fromtimestamp(maximum_ms / 1000, tz=UTC).date()
    windows = _session_windows(start, end).sort("pre_open_ms")

    joined = frame.sort("observed_timestamp_ms").join_asof(
        windows,
        left_on="observed_timestamp_ms",
        right_on="pre_open_ms",
        strategy="backward",
    )

    joined = joined.with_columns(
        pl.when(
            pl.col("session_date").is_null()
            | (pl.col("observed_timestamp_ms") > pl.col("after_close_ms"))
        )
        .then(pl.lit("CLOSED"))
        .when(pl.col("observed_timestamp_ms") < pl.col("open_ms"))
        .then(pl.lit("PRE"))
        .when(pl.col("observed_timestamp_ms") <= pl.col("close_ms"))
        .then(pl.lit("REGULAR"))
        .otherwise(pl.lit("AFTER"))
        .alias("market_session")
    ).with_columns(
        pl.when(pl.col("market_session") == "CLOSED")
        .then(pl.lit(None, dtype=pl.String))
        .otherwise(pl.col("session_date"))
        .alias("session_date")
    )

    return joined.drop("pre_open_ms", "open_ms", "close_ms", "after_close_ms")


def _edge_bucket() -> pl.Expr:
    edge = pl.col("gross_convergence_edge_bps")
    return (
        pl.when(edge <= 0)
        .then(pl.lit("<=0"))
        .when(edge <= 5)
        .then(pl.lit("(0,5]"))
        .when(edge <= 10)
        .then(pl.lit("(5,10]"))
        .when(edge <= 25)
        .then(pl.lit("(10,25]"))
        .otherwise(pl.lit(">25"))
        .alias("edge_bucket")
    )


def _freshness_bucket() -> pl.Expr:
    age = pl.col("event_age_ms")
    return (
        pl.when(age <= 1_000)
        .then(pl.lit("0-1s"))
        .when(age <= 5_000)
        .then(pl.lit("1-5s"))
        .when(age <= 30_000)
        .then(pl.lit("5-30s"))
        .otherwise(pl.lit(">30s"))
        .alias("freshness_bucket")
    )


def prepare_signals(
    frame: pl.DataFrame,
    *,
    max_event_age_ms: int | None = 5_000,
    max_reference_lag_ms: int | None = None,
) -> pl.DataFrame:
    """Validate, clean and enrich collected observations for research."""
    _require_columns(frame)

    cleaned = frame.filter(
        (pl.col("observed_timestamp_ms") > 0)
        & (pl.col("bid") > 0)
        & (pl.col("ask") >= pl.col("bid"))
        & (pl.col("mid") > 0)
    ).with_columns(
        pl.max_horizontal("book_age_ms", "reference_receive_age_ms").alias("event_age_ms"),
        pl.when(pl.col("long_convergence_bps") >= pl.col("short_convergence_bps"))
        .then(pl.lit("LONG"))
        .otherwise(pl.lit("SHORT"))
        .alias("preferred_side"),
    )

    if max_event_age_ms is not None:
        cleaned = cleaned.filter(pl.col("event_age_ms") <= max_event_age_ms)
    if max_reference_lag_ms is not None:
        cleaned = cleaned.filter(pl.col("reference_lag_ms") <= max_reference_lag_ms)

    cleaned = cleaned.with_columns(_edge_bucket(), _freshness_bucket())
    return label_us_equity_sessions(cleaned)


def forward_outcomes(
    signals: pl.DataFrame,
    *,
    horizons_s: tuple[int, ...] = (1, 5, 30, 300),
    max_match_lag_ms: int = 2_000,
) -> pl.DataFrame:
    """Join each signal to the first same-symbol observation at/after each target horizon."""
    if not horizons_s or any(horizon <= 0 for horizon in horizons_s):
        raise ValueError("horizons_s must contain positive integers")
    if max_match_lag_ms < 0:
        raise ValueError("max_match_lag_ms must be non-negative")
    if signals.is_empty():
        return signals.with_columns(
            pl.lit(None, dtype=pl.Int64).alias("horizon_s"),
            pl.lit(None, dtype=pl.Float64).alias("forward_trade_return_bps"),
        ).head(0)

    future = signals.select(
        "symbol",
        "observed_timestamp_ms",
        "bid",
        "ask",
        "mid",
        "basis_bps",
    )
    outcomes: list[pl.DataFrame] = []

    for horizon_s in horizons_s:
        future_timestamp = f"_future_timestamp_ms"
        future_frame = (
            future.rename(
                {
                    "observed_timestamp_ms": future_timestamp,
                    "bid": "_future_bid",
                    "ask": "_future_ask",
                    "mid": "_future_mid",
                    "basis_bps": "_future_basis_bps",
                }
            )
            .sort("symbol", future_timestamp)
        )

        joined = (
            signals.with_columns(
                (pl.col("observed_timestamp_ms") + horizon_s * 1_000).alias("_target_timestamp_ms")
            )
            .sort("symbol", "_target_timestamp_ms")
            .join_asof(
                future_frame,
                left_on="_target_timestamp_ms",
                right_on=future_timestamp,
                by="symbol",
                strategy="forward",
                tolerance=max_match_lag_ms,
            )
            .with_columns(
                pl.lit(horizon_s).alias("horizon_s"),
                (pl.col(future_timestamp) - pl.col("_target_timestamp_ms")).alias(
                    "forward_match_lag_ms"
                ),
                ((pl.col("_future_mid") / pl.col("mid") - 1.0) * 10_000.0).alias(
                    "forward_mid_return_bps"
                ),
                (
                    pl.col("basis_bps").abs() - pl.col("_future_basis_bps").abs()
                ).alias("basis_convergence_bps"),
                pl.when(pl.col("preferred_side") == "LONG")
                .then((pl.col("_future_bid") / pl.col("ask") - 1.0) * 10_000.0)
                .otherwise((1.0 - pl.col("_future_ask") / pl.col("bid")) * 10_000.0)
                .alias("forward_trade_return_bps"),
            )
            .drop(
                "_target_timestamp_ms",
                "_future_bid",
                "_future_ask",
                "_future_mid",
                "_future_basis_bps",
            )
        )
        outcomes.append(joined)

    return pl.concat(outcomes, how="vertical_relaxed").sort(
        "observed_timestamp_ms", "symbol", "horizon_s"
    )


def summarize_forward_outcomes(outcomes: pl.DataFrame) -> pl.DataFrame:
    """Aggregate forward executable returns by horizon, session, freshness, edge and side."""
    if outcomes.is_empty():
        return pl.DataFrame()

    return (
        outcomes.group_by(
            "horizon_s",
            "market_session",
            "freshness_bucket",
            "edge_bucket",
            "preferred_side",
        )
        .agg(
            pl.len().alias("signals"),
            pl.col("forward_trade_return_bps").count().alias("matched"),
            pl.col("gross_convergence_edge_bps").mean().alias("mean_signal_edge_bps"),
            pl.col("forward_trade_return_bps").mean().alias("mean_forward_trade_bps"),
            pl.col("forward_trade_return_bps").median().alias("median_forward_trade_bps"),
            (pl.col("forward_trade_return_bps") > 0).mean().alias("positive_rate"),
            pl.col("forward_trade_return_bps")
            .quantile(0.05, interpolation="linear")
            .alias("p05_forward_trade_bps"),
            pl.col("forward_trade_return_bps")
            .quantile(0.95, interpolation="linear")
            .alias("p95_forward_trade_bps"),
            pl.col("basis_convergence_bps").mean().alias("mean_basis_convergence_bps"),
            pl.col("reference_lag_ms").mean().alias("mean_reference_lag_ms"),
            pl.col("event_age_ms").mean().alias("mean_event_age_ms"),
        )
        .sort(
            "horizon_s",
            "market_session",
            "freshness_bucket",
            "edge_bucket",
            "preferred_side",
        )
    )


def analyze_file(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    horizons_s: tuple[int, ...] = (1, 5, 30, 300),
    max_event_age_ms: int | None = 5_000,
    max_reference_lag_ms: int | None = None,
    max_match_lag_ms: int = 2_000,
) -> pl.DataFrame:
    """Run the full offline research pass and persist enriched datasets."""
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(source)

    raw = pl.read_csv(source)
    signals = prepare_signals(
        raw,
        max_event_age_ms=max_event_age_ms,
        max_reference_lag_ms=max_reference_lag_ms,
    )
    if signals.is_empty():
        raise ValueError("No usable observations remain after cleaning")

    outcomes = forward_outcomes(
        signals,
        horizons_s=horizons_s,
        max_match_lag_ms=max_match_lag_ms,
    )
    summary = summarize_forward_outcomes(outcomes)

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    signals.write_parquet(target / "signals.parquet")
    outcomes.write_parquet(target / "forward_outcomes.parquet")
    summary.write_csv(target / "forward_summary.csv")
    return summary


def _parse_horizons(raw: str) -> tuple[int, ...]:
    horizons = tuple(int(item.strip()) for item in raw.split(",") if item.strip())
    if not horizons or any(value <= 0 for value in horizons):
        raise argparse.ArgumentTypeError("horizons must be positive comma-separated seconds")
    return horizons


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze collected bStocks basis observations and forward executable returns"
    )
    parser.add_argument("--input", default="data/stream_basis.csv")
    parser.add_argument("--output-dir", default="data/research")
    parser.add_argument("--horizons", type=_parse_horizons, default=(1, 5, 30, 300))
    parser.add_argument("--max-event-age-ms", type=int, default=5_000)
    parser.add_argument("--max-reference-lag-ms", type=int)
    parser.add_argument("--max-match-lag-ms", type=int, default=2_000)
    return parser


def main() -> None:
    args = _parser().parse_args()
    summary = analyze_file(
        args.input,
        args.output_dir,
        horizons_s=args.horizons,
        max_event_age_ms=args.max_event_age_ms,
        max_reference_lag_ms=args.max_reference_lag_ms,
        max_match_lag_ms=args.max_match_lag_ms,
    )
    print(summary)


if __name__ == "__main__":
    main()
