"""Core decision-support contracts for QuantOs.

These types describe what the platform communicates to a human decision-maker.
They intentionally do not contain order-routing or execution methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from .time import as_utc


class EvidenceDomain(StrEnum):
    MARKET = "MARKET"
    MICROSTRUCTURE = "MICROSTRUCTURE"
    STRATEGY = "STRATEGY"
    REGIME = "REGIME"
    RISK = "RISK"
    LIQUIDITY = "LIQUIDITY"
    FUNDAMENTAL = "FUNDAMENTAL"
    EVENT = "EVENT"
    ANOMALY = "ANOMALY"
    DATA_QUALITY = "DATA_QUALITY"
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
    available_at: datetime | None = None

    def __post_init__(self) -> None:
        observed = as_utc(self.observed_at)
        available = observed if self.available_at is None else as_utc(self.available_at)
        if available < observed:
            raise ValueError("evidence cannot be available before it is observed")
        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "available_at", available)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not -1.0 <= self.directional_score <= 1.0:
            raise ValueError("directional_score must be between -1 and 1")

    def require_available(self, as_of: datetime) -> None:
        if (self.available_at or self.observed_at) > as_utc(as_of):
            raise ValueError(f"evidence from {self.source} is not available at the review cutoff")


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
    decision_score: float = 0.0
    priority_score: float = 0.0
    supporting_evidence: tuple[str, ...] = ()
    contradicting_evidence: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "as_of", as_utc(self.as_of))
        for item in self.evidence:
            item.require_available(self.as_of)
        if not self.instrument:
            raise ValueError("instrument is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not -1.0 <= self.decision_score <= 1.0:
            raise ValueError("decision_score must be between -1 and 1")
        if not 0.0 <= self.priority_score <= 1.0:
            raise ValueError("priority_score must be between 0 and 1")
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

    def __post_init__(self) -> None:
        object.__setattr__(self, "as_of", as_utc(self.as_of))
        if any(candidate.as_of > self.as_of for candidate in self.candidates):
            raise ValueError("candidate is newer than the decision snapshot")
