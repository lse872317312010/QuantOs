from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from bstocks_alpha.streaming import LiveBasisState, _select_instruments
from bstocks_alpha.universe import BStockInstrument


def instrument(symbol: str = "SPYBUSDT") -> BStockInstrument:
    return BStockInstrument(symbol, symbol.removesuffix("USDT"), "USDT", "TRADING", 2)


def test_live_state_pairs_book_and_reference_events() -> None:
    state = LiveBasisState()
    state.on_book(
        SimpleNamespace(s="SPYBUSDT", b="99.0", a="100.0", u=42),
        received_timestamp_ms=1_000,
    )
    state.on_reference(
        SimpleNamespace(s="SPYBUSDT", r="101.0", t=900),
        received_timestamp_ms=1_100,
    )

    observations = state.observations(
        [instrument()],
        observed=datetime.fromtimestamp(1.2, tz=UTC),
    )

    assert len(observations) == 1
    item = observations[0]
    assert item.book_update_id == 42
    assert item.book_age_ms == 200
    assert item.reference_receive_age_ms == 100
    assert item.reference_lag_ms == 300
    assert item.long_convergence_bps == pytest.approx(100.0)


def test_live_state_requires_both_event_types() -> None:
    state = LiveBasisState()
    state.on_book(
        SimpleNamespace(s="SPYBUSDT", b="99.0", a="100.0", u=42),
        received_timestamp_ms=1_000,
    )
    assert state.observations([instrument()]) == []


def test_select_instruments_rejects_unknown_symbol() -> None:
    instruments = [instrument()]
    with pytest.raises(ValueError, match="not discovered bStocks"):
        _select_instruments(instruments, {"NOTREALBUSDT"})
