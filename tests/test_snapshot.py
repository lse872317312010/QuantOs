import pytest

from bstocks_alpha.snapshot import _observation
from bstocks_alpha.universe import BStockInstrument


def test_observation_uses_midpoint_and_reference_price() -> None:
    instrument = BStockInstrument("SPYBUSDT", "SPYB", "USDT", "TRADING", 2)
    result = _observation(
        instrument,
        {"symbol": "SPYBUSDT", "bidPrice": "100", "askPrice": "102"},
        {"symbol": "SPYBUSDT", "referencePrice": "100", "timestamp": 123},
        observed_at_utc="2026-09-30T00:00:00+00:00",
        observed_timestamp_ms=223,
    )
    assert result.mid == pytest.approx(101.0)
    assert result.basis_bps == pytest.approx(100.0)
    assert result.spread_bps == pytest.approx(198.01980198)
    assert result.reference_lag_ms == 100
    assert result.long_convergence_bps == pytest.approx((100 / 102 - 1) * 10_000)
    assert result.short_convergence_bps == pytest.approx(0.0)
    assert result.gross_convergence_edge_bps == pytest.approx(0.0)


def test_observation_finds_positive_long_convergence_edge() -> None:
    instrument = BStockInstrument("SPYBUSDT", "SPYB", "USDT", "TRADING", 2)
    result = _observation(
        instrument,
        {"symbol": "SPYBUSDT", "bidPrice": "98", "askPrice": "99"},
        {"symbol": "SPYBUSDT", "referencePrice": "100", "timestamp": 123},
        observed_at_utc="2026-09-30T00:00:00+00:00",
        observed_timestamp_ms=223,
    )
    assert result.long_convergence_bps == pytest.approx((100 / 99 - 1) * 10_000)
    assert result.gross_convergence_edge_bps == pytest.approx(result.long_convergence_bps)


def test_observation_finds_positive_short_convergence_edge() -> None:
    instrument = BStockInstrument("SPYBUSDT", "SPYB", "USDT", "TRADING", 2)
    result = _observation(
        instrument,
        {"symbol": "SPYBUSDT", "bidPrice": "101", "askPrice": "102"},
        {"symbol": "SPYBUSDT", "referencePrice": "100", "timestamp": 123},
        observed_at_utc="2026-09-30T00:00:00+00:00",
        observed_timestamp_ms=223,
    )
    assert result.short_convergence_bps == pytest.approx(100.0)
    assert result.gross_convergence_edge_bps == pytest.approx(100.0)
