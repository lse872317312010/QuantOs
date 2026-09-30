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
    )
    assert result.mid == pytest.approx(101.0)
    assert result.basis_bps == pytest.approx(100.0)
    assert result.spread_bps == pytest.approx(198.01980198)
