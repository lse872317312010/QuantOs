from datetime import datetime

import pytest

from bstocks_alpha.snapshot import _observation
from bstocks_alpha.universe import BStockInstrument


def test_rest_snapshot_records_each_pair_only_after_reference_returns(monkeypatch):
    from bstocks_alpha import snapshot

    class Clock:
        def __init__(self):
            self.ms = 1000

        def now(self, tz):
            return datetime.fromtimestamp(self.ms / 1000, tz)

    clock = Clock()
    monkeypatch.setattr(snapshot, "datetime", clock)
    monkeypatch.setattr(snapshot, "book_tickers", lambda client: [
        {"symbol": symbol, "bidPrice": 10, "askPrice": 12} for symbol in ("A", "B")
    ])

    def delayed_reference(symbol, client):
        clock.ms += 1000
        return {"referencePrice": 11, "timestamp": 900}

    monkeypatch.setattr(snapshot, "reference_price", delayed_reference)
    batch = snapshot.collect_basis_snapshot([
        BStockInstrument(symbol, symbol, "USDT", "TRADING", 1) for symbol in ("A", "B")
    ])
    assert [row.observed_timestamp_ms for row in batch.observations] == [2000, 3000]
    assert [row.available_timestamp_ms for row in batch.observations] == [2000, 3000]
    assert [row.book_age_ms for row in batch.observations] == [1000, 2000]


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
