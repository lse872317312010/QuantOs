from datetime import UTC, datetime

import pytest
from quantos import (
    DecisionCandidate,
    DecisionStance,
    DecisionState,
    Evidence,
    EvidenceDomain,
    RiskAssessment,
)


NOW = datetime(2026, 10, 4, tzinfo=UTC)


def test_evidence_validates_confidence_and_direction() -> None:
    evidence = Evidence(
        domain=EvidenceDomain.MARKET,
        source="example",
        summary="basis widened",
        observed_at=NOW,
        confidence=0.8,
        directional_score=0.4,
    )
    assert evidence.confidence == 0.8

    with pytest.raises(ValueError, match="confidence"):
        Evidence(
            domain=EvidenceDomain.MARKET,
            source="example",
            summary="invalid",
            observed_at=NOW,
            confidence=1.1,
        )


def test_candidate_cannot_ignore_risk_blocker() -> None:
    with pytest.raises(ValueError, match="blocked candidates"):
        DecisionCandidate(
            instrument="SPYBUSDT",
            stance=DecisionStance.FAVOR_LONG,
            state=DecisionState.CANDIDATE,
            thesis="example",
            confidence=0.7,
            horizon="5m",
            evidence=(),
            risk=RiskAssessment(overall_score=0.8, blockers=("liquidity",)),
            as_of=NOW,
        )


def test_candidate_is_decision_support_not_execution_instruction() -> None:
    candidate = DecisionCandidate(
        instrument="SPYBUSDT",
        stance=DecisionStance.WATCH,
        state=DecisionState.INVESTIGATE,
        thesis="reference basis deserves review",
        confidence=0.6,
        horizon="intraday",
        evidence=(),
        risk=RiskAssessment(overall_score=0.3),
        as_of=NOW,
    )

    assert not hasattr(candidate, "submit_order")
    assert not hasattr(candidate, "execute")
