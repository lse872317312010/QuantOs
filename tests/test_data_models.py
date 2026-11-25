from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from quantos.data import (
    DataQualityState,
    DataSource,
    Instrument,
    MarketEvent,
    MarketEventType,
    assess_data_quality,
)

NOW = datetime(2026, 10, 4, 0, 0, tzinfo=UTC)


def test_market_event_requires_aware_monotonic_timestamps() -> None:
    event = MarketEvent(
        source_id="binance.book",
        instrument_id="SPYBUSDT.BINANCE",
        event_type=MarketEventType.QUOTE,
        ts_event=NOW,
        ts_received=NOW + timedelta(milliseconds=10),
        payload={"bid": 100.0, "ask": 100.1},
    )
    assert event.event_type is MarketEventType.QUOTE

    with pytest.raises(ValueError, match="timezone-aware"):
        MarketEvent(
            source_id="binance.book",
            instrument_id="SPYBUSDT.BINANCE",
            event_type=MarketEventType.QUOTE,
            ts_event=NOW.replace(tzinfo=None),
            ts_received=NOW,
        )


def test_quality_marks_stale_and_incomplete_without_inventing_observations() -> None:
    source = DataSource(
        source_id="binance.book",
        provider="binance",
        dataset="bookTicker",
        source_type="websocket",
        expected_interval_s=1.0,
    )

    stale = assess_data_quality(
        source,
        as_of=NOW,
        last_event_at=NOW - timedelta(seconds=4),
        observed_count=10,
        expected_count=10,
    )
    assert stale.state is DataQualityState.STALE

    incomplete = assess_data_quality(
        source,
        as_of=NOW,
        last_event_at=NOW - timedelta(milliseconds=100),
        observed_count=8,
        expected_count=10,
    )
    assert incomplete.state is DataQualityState.INCOMPLETE
    assert incomplete.completeness == pytest.approx(0.8)


def test_quote_age_uses_elapsed_seconds_in_repeated_hour() -> None:
    ny = ZoneInfo("America/New_York")
    first = datetime(2026, 11, 1, 1, 45, tzinfo=ny, fold=0)
    later = datetime(2026, 11, 1, 1, 15, tzinfo=ny, fold=1)
    source = DataSource("s", "p", "quotes", "parquet", expected_interval_s=1)
    report = assess_data_quality(source, as_of=later, last_event_at=first, observed_count=1)
    assert report.freshness_s == 1800
    assert report.state is DataQualityState.STALE
    with pytest.raises(ValueError, match="newer"):
        assess_data_quality(source, as_of=first, last_event_at=later, observed_count=1)


def test_instrument_identity_keeps_raw_symbol_separate() -> None:
    instrument = Instrument(
        instrument_id="SPYBUSDT.BINANCE",
        symbol="SPYBUSDT",
        raw_symbol="SPYBUSDT",
        venue="BINANCE",
        asset_class="TOKENIZED_EQUITY",
        quote_currency="USDT",
    )
    assert instrument.instrument_id.endswith(".BINANCE")
