from dataclasses import replace
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from quantos.contracts import (
    DecisionStance,
    DecisionState,
    Evidence,
    EvidenceDomain,
    RiskAssessment,
)
from quantos.decision import DecisionJournal, RuleBasedDecisionSynthesizer, SynthesisConfig

NOW = datetime(2026, 11, 24, tzinfo=UTC)


def ev(
    score: float,
    confidence: float,
    summary: str,
    *,
    domain: EvidenceDomain = EvidenceDomain.STRATEGY,
) -> Evidence:
    return Evidence(
        domain=domain,
        source="test",
        summary=summary,
        observed_at=NOW,
        confidence=confidence,
        directional_score=score,
        metadata={"horizon": "intraday"},
    )


def test_synthesizer_ranks_strong_candidate_ahead_of_weak_one() -> None:
    synthesizer = RuleBasedDecisionSynthesizer()
    snapshot = synthesizer.synthesize(
        as_of=NOW,
        evidence_by_instrument={
            "STRONG": (ev(0.9, 0.9, "strong positive"),),
            "WEAK": (ev(0.1, 0.6, "weak positive"),),
        },
        risk_by_instrument={
            "STRONG": RiskAssessment(overall_score=0.1),
            "WEAK": RiskAssessment(overall_score=0.1),
        },
        market_context={},
    )

    assert snapshot.candidates[0].instrument == "STRONG"
    assert snapshot.candidates[0].state is DecisionState.CANDIDATE
    assert snapshot.candidates[0].stance is DecisionStance.FAVOR_LONG
    assert snapshot.candidates[0].priority_score > snapshot.candidates[1].priority_score


def test_contradicting_evidence_reduces_confidence() -> None:
    synthesizer = RuleBasedDecisionSynthesizer()
    clean = synthesizer.synthesize(
        as_of=NOW,
        evidence_by_instrument={"X": (ev(0.8, 0.9, "positive"),)},
        risk_by_instrument={"X": RiskAssessment(overall_score=0.0)},
        market_context={},
    ).candidates[0]
    mixed = synthesizer.synthesize(
        as_of=NOW,
        evidence_by_instrument={
            "X": (
                ev(0.8, 0.9, "positive"),
                ev(-0.7, 0.8, "negative", domain=EvidenceDomain.MICROSTRUCTURE),
            )
        },
        risk_by_instrument={"X": RiskAssessment(overall_score=0.0)},
        market_context={},
    ).candidates[0]

    assert mixed.confidence < clean.confidence
    assert mixed.contradicting_evidence == ("negative",)


def test_risk_blocker_forces_blocked_avoid_state() -> None:
    synthesizer = RuleBasedDecisionSynthesizer()
    candidate = synthesizer.synthesize(
        as_of=NOW,
        evidence_by_instrument={"X": (ev(1.0, 1.0, "very strong"),)},
        risk_by_instrument={
            "X": RiskAssessment(
                overall_score=0.9,
                blockers=("data stale",),
                warnings=("spread wide",),
            )
        },
        market_context={},
    ).candidates[0]

    assert candidate.state is DecisionState.BLOCKED
    assert candidate.stance is DecisionStance.AVOID
    assert candidate.priority_score == 0.0
    assert "data stale" in candidate.invalidation_conditions


def test_config_rejects_invalid_weight() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        SynthesisConfig(domain_weights={EvidenceDomain.STRATEGY: -1.0})


def test_missing_risk_assessment_blocks_only_the_affected_instrument() -> None:
    signal = (ev(1.0, 1.0, "strong"),)
    snapshot = RuleBasedDecisionSynthesizer().synthesize(
        as_of=NOW, evidence_by_instrument={"X": signal, "Y": signal},
        risk_by_instrument={"Y": RiskAssessment(overall_score=0.0)}, market_context={},
    )
    good, blocked = snapshot.candidates
    assert (good.instrument, good.state) == ("Y", DecisionState.CANDIDATE)
    assert (blocked.instrument, blocked.state) == ("X", DecisionState.BLOCKED)
    assert blocked.priority_score == 0
    assert blocked.risk.blockers


def test_synthesis_checks_actual_evidence_availability_across_fall_back() -> None:
    zone = ZoneInfo("America/New_York")
    observed = datetime(2026, 11, 1, 1, 45, tzinfo=zone, fold=0)
    received = datetime(2026, 11, 1, 1, 15, tzinfo=zone, fold=1)
    delayed = replace(ev(1.0, 1.0, "revised"), observed_at=observed, available_at=received)
    args = {
        "evidence_by_instrument": {"X": (delayed,)},
        "risk_by_instrument": {"X": RiskAssessment(0.0)}, "market_context": {},
    }
    synth = RuleBasedDecisionSynthesizer()
    with pytest.raises(ValueError, match="available"):
        synth.synthesize(as_of=observed, **args)
    snapshot = synth.synthesize(as_of=received, **args)
    assert snapshot.as_of.tzinfo is UTC
    assert snapshot.candidates[0].state is DecisionState.CANDIDATE


def test_decision_journal_round_trips_snapshot_as_jsonl(tmp_path) -> None:
    synthesizer = RuleBasedDecisionSynthesizer()
    snapshot = synthesizer.synthesize(
        as_of=NOW,
        evidence_by_instrument={"X": (ev(0.8, 0.9, "positive"),)},
        risk_by_instrument={"X": RiskAssessment(overall_score=0.1)},
        market_context={"session": "REGULAR"},
    )
    journal = DecisionJournal(tmp_path / "decision-journal.jsonl")
    journal.append(snapshot)

    entry = journal.entries()[0]
    assert entry["as_of"] == NOW.isoformat()
    assert entry["candidates"][0]["instrument"] == "X"
    assert entry["candidates"][0]["stance"] == "FAVOR_LONG"
