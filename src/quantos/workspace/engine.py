"""Analyst review-session orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quantos.contracts import DecisionSnapshot
from quantos.decision import DecisionJournal
from quantos.evidence import EvidenceEngine
from quantos.interfaces import DecisionSynthesizer
from quantos.risk import RiskEngine


@dataclass(frozen=True, slots=True)
class ReviewFailure:
    instrument: str
    stage: str
    provider: str
    error: str


@dataclass(frozen=True, slots=True)
class ReviewSession:
    """One reproducible multi-instrument analyst review."""

    snapshot: DecisionSnapshot
    failures: tuple[ReviewFailure, ...] = ()


class AnalystReviewEngine:
    """Run the evidence -> risk -> synthesis workflow for a watchlist."""

    def __init__(
        self,
        *,
        evidence_engine: EvidenceEngine,
        risk_engine: RiskEngine,
        synthesizer: DecisionSynthesizer,
        journal: DecisionJournal | None = None,
    ) -> None:
        self.evidence_engine = evidence_engine
        self.risk_engine = risk_engine
        self.synthesizer = synthesizer
        self.journal = journal

    def review(
        self,
        *,
        instruments: tuple[str, ...],
        as_of: datetime,
        context_by_instrument: dict[str, dict[str, Any]],
        market_context: dict[str, Any] | None = None,
    ) -> ReviewSession:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        evidence_by_instrument = {}
        risk_by_instrument = {}
        failures: list[ReviewFailure] = []

        for instrument in instruments:
            context = context_by_instrument.get(instrument, {})
            evidence_batch = self.evidence_engine.collect(
                instrument=instrument,
                as_of=as_of,
                context=context,
            )
            evidence_by_instrument[instrument] = evidence_batch.evidence
            failures.extend(
                ReviewFailure(
                    instrument=instrument,
                    stage="evidence",
                    provider=failure.provider,
                    error=failure.error,
                )
                for failure in evidence_batch.failures
            )

            risk_batch = self.risk_engine.assess(
                instrument=instrument,
                as_of=as_of,
                evidence=evidence_batch.evidence,
                context=context,
            )
            risk_by_instrument[instrument] = risk_batch.assessment
            failures.extend(
                ReviewFailure(
                    instrument=instrument,
                    stage="risk",
                    provider=failure.provider,
                    error=failure.error,
                )
                for failure in risk_batch.failures
            )

        snapshot = self.synthesizer.synthesize(
            as_of=as_of,
            evidence_by_instrument=evidence_by_instrument,
            risk_by_instrument=risk_by_instrument,
            market_context=market_context or {},
        )
        if self.journal is not None:
            self.journal.append(snapshot)
        return ReviewSession(snapshot=snapshot, failures=tuple(failures))
