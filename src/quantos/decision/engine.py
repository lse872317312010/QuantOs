"""Transparent decision synthesis for human review."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from quantos.contracts import (
    DecisionCandidate,
    DecisionSnapshot,
    DecisionStance,
    DecisionState,
    Evidence,
    EvidenceDomain,
    RiskAssessment,
)


@dataclass(frozen=True, slots=True)
class SynthesisConfig:
    """Explicit weights and thresholds used by the rule-based synthesizer."""

    domain_weights: dict[EvidenceDomain, float] = field(
        default_factory=lambda: {
            EvidenceDomain.STRATEGY: 1.0,
            EvidenceDomain.MICROSTRUCTURE: 0.9,
            EvidenceDomain.MARKET: 0.8,
            EvidenceDomain.REGIME: 0.7,
            EvidenceDomain.FUNDAMENTAL: 0.7,
            EvidenceDomain.EVENT: 0.7,
            EvidenceDomain.ANOMALY: 0.5,
            EvidenceDomain.LIQUIDITY: 0.3,
            EvidenceDomain.DATA_QUALITY: 0.2,
            EvidenceDomain.PORTFOLIO: 0.3,
            EvidenceDomain.RISK: 0.2,
        }
    )
    candidate_min_abs_score: float = 0.20
    candidate_min_confidence: float = 0.55
    watch_min_abs_score: float = 0.05
    risk_confidence_penalty: float = 0.50
    contradiction_confidence_penalty: float = 0.50

    def __post_init__(self) -> None:
        if not 0 <= self.candidate_min_abs_score <= 1:
            raise ValueError("candidate_min_abs_score must be between 0 and 1")
        if not 0 <= self.candidate_min_confidence <= 1:
            raise ValueError("candidate_min_confidence must be between 0 and 1")
        if not 0 <= self.watch_min_abs_score <= 1:
            raise ValueError("watch_min_abs_score must be between 0 and 1")
        if not 0 <= self.risk_confidence_penalty <= 1:
            raise ValueError("risk_confidence_penalty must be between 0 and 1")
        if not 0 <= self.contradiction_confidence_penalty <= 1:
            raise ValueError("contradiction_confidence_penalty must be between 0 and 1")
        invalid = {domain: value for domain, value in self.domain_weights.items() if value < 0}
        if invalid:
            raise ValueError(f"domain weights must be non-negative: {invalid}")


class RuleBasedDecisionSynthesizer:
    """Combine evidence and risk without hiding the scoring logic."""

    def __init__(self, config: SynthesisConfig | None = None) -> None:
        self.config = config or SynthesisConfig()

    def synthesize(
        self,
        *,
        as_of: datetime,
        evidence_by_instrument: dict[str, tuple[Evidence, ...]],
        risk_by_instrument: dict[str, RiskAssessment],
        market_context: dict[str, Any],
    ) -> DecisionSnapshot:
        candidates = [
            self._candidate(
                instrument=instrument,
                as_of=as_of,
                evidence=tuple(evidence),
                risk=risk_by_instrument.get(instrument) or RiskAssessment(
                    overall_score=1.0, blockers=("risk assessment unavailable",),
                ),
            )
            for instrument, evidence in evidence_by_instrument.items()
        ]
        candidates.sort(
            key=lambda item: (
                item.state is DecisionState.BLOCKED,
                -item.priority_score,
                item.instrument,
            )
        )
        alerts = tuple(
            f"{candidate.instrument}: {blocker}"
            for candidate in candidates
            for blocker in candidate.risk.blockers
        )
        return DecisionSnapshot(
            as_of=as_of,
            market_context=market_context,
            candidates=tuple(candidates),
            alerts=alerts,
            notes=(
                "Candidates are ranked for human review; ranking is not an execution instruction.",
            ),
        )

    def _candidate(
        self,
        *,
        instrument: str,
        as_of: datetime,
        evidence: tuple[Evidence, ...],
        risk: RiskAssessment,
    ) -> DecisionCandidate:
        score, base_confidence, contradiction_ratio = self._aggregate(evidence)
        confidence = base_confidence
        confidence *= 1.0 - self.config.contradiction_confidence_penalty * contradiction_ratio
        confidence *= 1.0 - self.config.risk_confidence_penalty * risk.overall_score
        confidence = max(0.0, min(1.0, confidence))

        if risk.blockers:
            stance = DecisionStance.AVOID
            state = DecisionState.BLOCKED
        else:
            stance = self._stance(score)
            if (
                abs(score) >= self.config.candidate_min_abs_score
                and confidence >= self.config.candidate_min_confidence
            ):
                state = DecisionState.CANDIDATE
            elif evidence:
                state = DecisionState.INVESTIGATE
            else:
                state = DecisionState.OBSERVE

        supporting, contradicting = self._split_evidence(evidence, score)
        thesis = self._thesis(instrument, stance, supporting, risk)
        invalidation = tuple(
            dict.fromkeys(
                [item.summary for item in contradicting[:3]]
                + list(risk.warnings)
                + list(risk.blockers)
            )
        )
        alternatives = self._alternatives(stance)
        priority_score = confidence * abs(score) * (1.0 - risk.overall_score)
        if state is DecisionState.BLOCKED:
            priority_score = 0.0

        return DecisionCandidate(
            instrument=instrument,
            stance=stance,
            state=state,
            thesis=thesis,
            confidence=confidence,
            horizon=self._horizon(evidence),
            evidence=evidence,
            risk=risk,
            as_of=as_of,
            tags=tuple(sorted({item.domain.value.lower() for item in evidence})),
            decision_score=score,
            priority_score=priority_score,
            supporting_evidence=tuple(item.summary for item in supporting),
            contradicting_evidence=tuple(item.summary for item in contradicting),
            invalidation_conditions=invalidation,
            alternatives=alternatives,
        )

    def _aggregate(self, evidence: tuple[Evidence, ...]) -> tuple[float, float, float]:
        directional = [item for item in evidence if item.directional_score != 0]
        if not directional:
            confidence = (
                sum(item.confidence for item in evidence) / len(evidence) if evidence else 0.0
            )
            return 0.0, confidence, 0.0

        weighted_score = 0.0
        total_weight = 0.0
        confidence_weighted = 0.0
        positive_weight = 0.0
        negative_weight = 0.0

        for item in directional:
            domain_weight = self.config.domain_weights.get(item.domain, 0.5)
            weight = domain_weight * item.confidence
            weighted_score += item.directional_score * weight
            confidence_weighted += item.confidence * domain_weight
            total_weight += weight
            if item.directional_score > 0:
                positive_weight += weight
            else:
                negative_weight += weight

        if total_weight <= 0:
            return 0.0, 0.0, 0.0

        score = max(-1.0, min(1.0, weighted_score / total_weight))
        weight_denominator = sum(
            self.config.domain_weights.get(item.domain, 0.5) for item in directional
        )
        base_confidence = (
            confidence_weighted / weight_denominator if weight_denominator > 0 else 0.0
        )
        opposing = min(positive_weight, negative_weight)
        contradiction_ratio = opposing / total_weight
        return score, base_confidence, contradiction_ratio

    def _split_evidence(
        self,
        evidence: tuple[Evidence, ...],
        score: float,
    ) -> tuple[list[Evidence], list[Evidence]]:
        if score > 0:
            supporting = [item for item in evidence if item.directional_score > 0]
            contradicting = [item for item in evidence if item.directional_score < 0]
        elif score < 0:
            supporting = [item for item in evidence if item.directional_score < 0]
            contradicting = [item for item in evidence if item.directional_score > 0]
        else:
            supporting = [item for item in evidence if item.directional_score == 0]
            contradicting = []
        def evidence_sort_key(item: Evidence) -> tuple[float, str, str, str]:
            return (-item.confidence, item.domain.value, item.source, item.summary)

        supporting.sort(key=evidence_sort_key)
        contradicting.sort(key=evidence_sort_key)
        return supporting, contradicting

    def _stance(self, score: float) -> DecisionStance:
        if score >= self.config.candidate_min_abs_score:
            return DecisionStance.FAVOR_LONG
        if score <= -self.config.candidate_min_abs_score:
            return DecisionStance.FAVOR_SHORT
        if abs(score) >= self.config.watch_min_abs_score:
            return DecisionStance.WATCH
        return DecisionStance.NEUTRAL

    @staticmethod
    def _horizon(evidence: tuple[Evidence, ...]) -> str:
        horizons = [
            str(item.metadata["horizon"])
            for item in evidence
            if item.metadata.get("horizon") is not None
        ]
        return horizons[0] if horizons else "unspecified"

    @staticmethod
    def _thesis(
        instrument: str,
        stance: DecisionStance,
        supporting: list[Evidence],
        risk: RiskAssessment,
    ) -> str:
        if risk.blockers:
            return f"{instrument} is blocked: {risk.blockers[0]}"
        if supporting:
            return f"{stance.value}: {supporting[0].summary}"
        return f"{stance.value}: no directional evidence dominates"

    @staticmethod
    def _alternatives(stance: DecisionStance) -> tuple[str, ...]:
        if stance in {DecisionStance.FAVOR_LONG, DecisionStance.FAVOR_SHORT}:
            return ("wait for stronger confirmation", "remain neutral")
        if stance is DecisionStance.AVOID:
            return ("avoid new exposure", "reassess after blockers clear")
        return ("continue monitoring",)
