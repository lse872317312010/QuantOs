"""Canonical analytical-data contracts for QuantOs.

These are deliberately thin normalization types. Exchange-/vendor-specific payloads stay in
adapters, while richer trading-engine instrument semantics can map to upstream models such as
NautilusTrader.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MarketEventType(StrEnum):
    QUOTE = "QUOTE"
    TRADE = "TRADE"
    BAR = "BAR"
    REFERENCE_PRICE = "REFERENCE_PRICE"
    FUNDING = "FUNDING"
    STATUS = "STATUS"
    CUSTOM = "CUSTOM"


class DataQualityState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    INCOMPLETE = "INCOMPLETE"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class Instrument:
    """Stable cross-source identity for an analytical instrument."""

    instrument_id: str
    symbol: str
    venue: str
    asset_class: str
    quote_currency: str | None = None
    base_currency: str | None = None
    underlying_id: str | None = None
    raw_symbol: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.instrument_id or not self.symbol or not self.venue:
            raise ValueError("instrument_id, symbol and venue are required")


@dataclass(frozen=True, slots=True)
class DataSource:
    """Registered source with explicit provenance and expected update cadence."""

    source_id: str
    provider: str
    dataset: str
    source_type: str
    expected_interval_s: float | None = None
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id or not self.provider or not self.dataset:
            raise ValueError("source_id, provider and dataset are required")
        if self.expected_interval_s is not None and self.expected_interval_s <= 0:
            raise ValueError("expected_interval_s must be positive")


@dataclass(frozen=True, slots=True)
class MarketEvent:
    """Normalized point-in-time event with both event and receive timestamps."""

    source_id: str
    instrument_id: str
    event_type: MarketEventType
    ts_event: datetime
    ts_received: datetime
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.ts_event.tzinfo is None or self.ts_received.tzinfo is None:
            raise ValueError("market event timestamps must be timezone-aware")
        # Source clocks can be ahead of the receiver. Preserve both timestamps rather than
        # rewriting or rejecting the event; downstream quality logic can measure clock skew.


@dataclass(frozen=True, slots=True)
class DataQualityReport:
    """Health assessment for one source/instrument at a point in time."""

    source_id: str
    as_of: datetime
    state: DataQualityState
    freshness_s: float | None
    completeness: float | None
    last_event_at: datetime | None = None
    issues: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        if self.freshness_s is not None and self.freshness_s < 0:
            raise ValueError("freshness_s must be non-negative")
        if self.completeness is not None and not 0.0 <= self.completeness <= 1.0:
            raise ValueError("completeness must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """Point-in-time analytical snapshot assembled from one or more sources."""

    instrument_id: str
    as_of: datetime
    values: dict[str, Any]
    source_ids: tuple[str, ...]
    quality: tuple[DataQualityReport, ...] = ()

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")


def utc_now() -> datetime:
    """Small injectable-friendly default for callers that need an aware timestamp."""
    return datetime.now(UTC)
