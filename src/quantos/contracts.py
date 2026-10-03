"""Core decision-support contracts for QuantOs.

These types describe what the platform communicates to a human decision-maker.
They intentionally do not contain order-routing or execution methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class EvidenceDomain(StrEnum):
    MARKET = "MARKET"
    MICROSTRUCTURE = "MICROSTRUCTURE"
    STRATEGY = "STRATEGY"
    REGIME = "REGIME"
    RISK = "RISK"
    LIQUIDITY = "LIQUIDITY"
    FUNDAMENTAL = "FUNDAMENTAL"
    EVENT = "EVENT"
    PORTFOLIO = "PORTFOLIO"


class DecisionStance(StrEnum):
    FAVOR_LONG = "FAVOR_LONG"
    FAVOR_SHORT = "FAVOR_SHORT"
    NEUTRAL = "NEUTRAL"
    AVOID = "AVOID"
    WATCH = "WATCH"


class DecisionState(StrEnum):
    OBSERVE = "OBSERVE"
    INVESTIGATE = "INVESTIGATE"
    CANDIDATE = "CANDIDATE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class Evidence:
    """One auditable piece of evidence used in a decision view."""

    domain: EvidenceDomain
    source: str
    summary: str
    observed_at: datetime
    confidence: float
    directional_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not -1.0 <= self.directional_score <= 1.0:
            raise ValueError("directional_score must be between -1 and 1")


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Human-readable risk envelope attached to a candidate."""

    overall_score: float
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    dimensions: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.overall_score <= 1.0:
            raise ValueError("overall_score must be between 0 and 1")
        invalid = {
            name: value
            for name, value in self.dimensions.items()
            if not 0.0 <= value <= 1.0
        }
        if invalid:
            raise ValueError(f"risk dimensions must be between 0 and 1: {invalid}")


@dataclass(frozen=True, slots=True)
class DecisionCandidate:
    """A decision-support candidate presented for human review."""

    instrument: str
    stance: DecisionStance
    state: DecisionState
    thesis: str
    confidence: float
    horizon: str
    evidence: tuple[Evidence, ...]
    risk: RiskAssessment
    as_of: datetime
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.instrument:
            raise ValueError("instrument is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.risk.blockers and self.state is DecisionState.CANDIDATE:
            raise ValueError("blocked candidates cannot be in CANDIDATE state")


@dataclass(frozen=True, slots=True)
class DecisionSnapshot:
    """Point-in-time platform output for a human decision session."""

    as_of: datetime
    market_context: dict[str, Any]
    candidates: tuple[DecisionCandidate, ...] = ()
    alerts: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
