import polars as pl
import pytest

from bstocks_alpha.uncertainty import daily_net_summary, date_cluster_bootstrap


def outcome(
    market_date: str,
    net_bps: float,
    *,
    sample: str = "TEST",
    symbol: str = "SPYBUSDT",
) -> dict[str, object]:
    return {
        "sample": sample,
        "market_date": market_date,
        "horizon_s": 5,
        "market_session": "REGULAR",
        "edge_bucket": ">25",
        "preferred_side": "LONG",
        "symbol": symbol,
        "net_forward_trade_return_bps": net_bps,
        "gross_convergence_edge_bps": 40.0,
    }


def test_daily_summary_collapses_intraday_rows_to_one_date_cluster() -> None:
    frame = pl.DataFrame(
        [
            outcome("2026-09-28", 10.0),
            outcome("2026-09-28", 30.0),
            outcome("2026-09-29", -5.0),
        ]
    )
    daily = daily_net_summary(frame)
    assert daily.height == 2

    first = daily.filter(pl.col("market_date") == "2026-09-28").to_dicts()[0]
    assert first["matched_trades"] == 2
    assert first["daily_mean_net_bps"] == pytest.approx(20.0)


def test_date_cluster_bootstrap_constant_days_has_exact_interval() -> None:
    frame = pl.DataFrame(
        [outcome(f"2026-09-{day:02d}", 5.0) for day in range(20, 25)]
    )
    daily = daily_net_summary(frame)
    result = date_cluster_bootstrap(
        daily,
        resamples=200,
        confidence=0.95,
        min_dates=5,
        seed=123,
    ).to_dicts()[0]

    assert result["status"] == "OK"
    assert result["market_dates"] == 5
    assert result["ci_low_bps"] == pytest.approx(5.0)
    assert result["ci_high_bps"] == pytest.approx(5.0)
    assert result["ci_excludes_zero"] is True


def test_date_cluster_bootstrap_marks_small_samples_insufficient() -> None:
    frame = pl.DataFrame(
        [
            outcome("2026-09-28", 10.0),
            outcome("2026-09-29", -5.0),
        ]
    )
    daily = daily_net_summary(frame)
    result = date_cluster_bootstrap(daily, min_dates=5).to_dicts()[0]

    assert result["status"] == "INSUFFICIENT_DATES"
    assert result["market_dates"] == 2
    assert result["ci_low_bps"] is None
    assert result["ci_high_bps"] is None
    assert result["ci_excludes_zero"] is None
