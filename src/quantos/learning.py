"""Learning-domain contracts, not a graph store, agent runtime or backtest engine.

EvidenceLink refers to the platform's existing Evidence by identifier. Storage,
retrieval, orchestration and scoring remain responsibilities of upstream adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite


class KnowledgeKind(StrEnum):
    OBSERVATION = "OBSERVATION"
    INTERPRETATION = "INTERPRETATION"
    CAUSAL_HYPOTHESIS = "CAUSAL_HYPOTHESIS"


class EvidenceRole(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CONTEXT = "CONTEXT"


class ScoringStatus(StrEnum):
    PENDING_HORIZON = "PENDING_HORIZON"
    PENDING_OUTCOME = "PENDING_OUTCOME"
    PENDING_AVAILABILITY = "PENDING_AVAILABILITY"
    READY = "READY"


def _aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")


def _text(*values: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("text fields must not be blank")


def _strings(values: tuple[str, ...]) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError("a non-empty immutable tuple is required")
    _text(*values)


@dataclass(frozen=True, slots=True)
class EvidenceLink:
    """Provenance for one version of an Evidence item; not proof it is true."""

    evidence_id: str
    source_uri: str
    source_family: str
    content_sha256: str
    published_at: datetime
    first_seen_at: datetime
    recorded_at: datetime
    kind: KnowledgeKind
    role: EvidenceRole

    def __post_init__(self) -> None:
        _text(self.evidence_id, self.source_uri, self.source_family, self.content_sha256)
        if len(self.content_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.content_sha256
        ):
            raise ValueError("content_sha256 must be a lowercase SHA-256 digest")
        for value in (self.published_at, self.first_seen_at, self.recorded_at):
            _aware(value)
        if self.recorded_at < self.first_seen_at:
            raise ValueError("recorded_at cannot precede first_seen_at")
        if not isinstance(self.kind, KnowledgeKind) or not isinstance(self.role, EvidenceRole):
            raise ValueError("kind and role must use the declared enums")

    @property
    def available_at(self) -> datetime:
        """Conservative availability for live/paper knowledge, including extraction time."""
        return max(self.published_at, self.first_seen_at, self.recorded_at)


@dataclass(frozen=True, slots=True)
class HypothesisSpec:
    """A falsifiable, versioned research specification frozen before evaluation."""

    hypothesis_id: str
    version: int
    registered_at: datetime
    claim: str
    mechanism: str
    instruments: tuple[str, ...]
    horizon_seconds: int
    signal_definition: str
    benchmark: str
    falsification_rule: str
    counterarguments: tuple[str, ...]
    evidence: tuple[EvidenceLink, ...]

    def __post_init__(self) -> None:
        _aware(self.registered_at)
        _text(
            self.hypothesis_id, self.claim, self.mechanism, self.signal_definition,
            self.benchmark, self.falsification_rule,
        )
        _strings(self.instruments)
        _strings(self.counterarguments)
        if type(self.version) is not int or self.version < 1:
            raise ValueError("version must be a positive integer")
        if type(self.horizon_seconds) is not int or self.horizon_seconds < 1:
            raise ValueError("horizon_seconds must be a positive integer")
        if not isinstance(self.evidence, tuple) or not self.evidence:
            raise ValueError("evidence must be a non-empty immutable tuple")
        if any(not isinstance(item, EvidenceLink) for item in self.evidence):
            raise ValueError("evidence must contain EvidenceLink values")
        ids = [item.evidence_id for item in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate evidence identifiers")
        if any(item.available_at > self.registered_at for item in self.evidence):
            raise ValueError("evidence was unavailable when the hypothesis was registered")

    @property
    def source_family_count(self) -> int:
        """Count attributed origins, not independent confirmations or a confidence score."""
        return len({item.source_family for item in self.evidence})


@dataclass(frozen=True, slots=True)
class ForecastRegistration:
    """An immutable probability prediction, distinct from an investment instruction."""

    forecast_id: str
    hypothesis: HypothesisSpec
    registered_at: datetime
    target_end: datetime
    event_definition: str
    probability: float

    def __post_init__(self) -> None:
        _text(self.forecast_id, self.event_definition)
        _aware(self.registered_at)
        _aware(self.target_end)
        if not isinstance(self.hypothesis, HypothesisSpec):
            raise ValueError("hypothesis must be a HypothesisSpec")
        if self.registered_at < self.hypothesis.registered_at:
            raise ValueError("forecast cannot precede its hypothesis")
        if (self.target_end - self.registered_at).total_seconds() != self.hypothesis.horizon_seconds:
            raise ValueError("target_end must match the pre-registered horizon")
        if isinstance(self.probability, bool) or not isfinite(self.probability):
            raise ValueError("probability must be finite")
        if not 0 <= self.probability <= 1:
            raise ValueError("probability must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class OutcomeObservation:
    """A finalized binary label from an explicitly versioned source."""

    forecast_id: str
    target_end: datetime
    available_at: datetime
    occurred: bool
    source_uri: str
    dataset_version: str

    def __post_init__(self) -> None:
        _text(self.forecast_id, self.source_uri, self.dataset_version)
        _aware(self.target_end)
        _aware(self.available_at)
        if self.available_at < self.target_end:
            raise ValueError("a finalized outcome cannot be available before its window closes")
        if type(self.occurred) is not bool:
            raise ValueError("occurred must be a finalized boolean label")


def scoring_status(
    forecast: ForecastRegistration,
    outcome: OutcomeObservation | None,
    *,
    as_of: datetime,
) -> ScoringStatus:
    """Gate mature labels; use an upstream metric library for actual calibration scores."""
    _aware(as_of)
    if outcome is not None and (
        outcome.forecast_id != forecast.forecast_id or outcome.target_end != forecast.target_end
    ):
        raise ValueError("outcome does not belong to this forecast and horizon")
    if as_of < forecast.target_end:
        return ScoringStatus.PENDING_HORIZON
    if outcome is None:
        return ScoringStatus.PENDING_OUTCOME
    if outcome.available_at > as_of:
        return ScoringStatus.PENDING_AVAILABILITY
    return ScoringStatus.READY
