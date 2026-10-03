"""Extension interfaces for QuantOs analytical providers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, Sequence

from .contracts import DecisionSnapshot, Evidence, RiskAssessment


class EvidenceProvider(Protocol):
    """Produces timestamped analytical evidence without making the final decision."""

    @property
    def name(self) -> str: ...

    def collect_evidence(
        self,
        *,
        instrument: str,
        as_of: datetime,
        context: dict[str, Any],
    ) -> Sequence[Evidence]: ...


class RiskProvider(Protocol):
    """Assesses risk and may return hard blockers for a human-reviewed candidate."""

    @property
    def name(self) -> str: ...

    def assess(
        self,
        *,
        instrument: str,
        as_of: datetime,
        evidence: Sequence[Evidence],
        context: dict[str, Any],
    ) -> RiskAssessment: ...


class DecisionSynthesizer(Protocol):
    """Combines evidence and risk into a human-facing decision snapshot."""

    def synthesize(
        self,
        *,
        as_of: datetime,
        evidence_by_instrument: dict[str, Sequence[Evidence]],
        risk_by_instrument: dict[str, RiskAssessment],
        market_context: dict[str, Any],
    ) -> DecisionSnapshot: ...
