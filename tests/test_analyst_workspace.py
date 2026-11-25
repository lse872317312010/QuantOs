from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from quantos.contracts import DecisionState, Evidence, EvidenceDomain, RiskAssessment
from quantos.decision import DecisionJournal, RuleBasedDecisionSynthesizer
from quantos.evidence import EvidenceEngine
from quantos.risk import RiskEngine
from quantos.workspace import AnalystReviewEngine, render_markdown

NOW = datetime(2026, 11, 24, tzinfo=UTC)


class SignalProvider:
    @property
    def name(self) -> str:
        return "signal"

    def collect_evidence(
        self,
        *,
        instrument: str,
        as_of: datetime,
        context: dict[str, Any],
    ) -> Sequence[Evidence]:
        return (
            Evidence(
                domain=EvidenceDomain.STRATEGY,
                source=self.name,
                summary=f"{instrument} positive signal",
                observed_at=as_of,
                confidence=0.9,
                directional_score=float(context.get("score", 0.8)),
                metadata={"horizon": "intraday"},
            ),
        )


class TestRiskProvider:
    @property
    def name(self) -> str:
        return "test-risk"

    def assess(
        self,
        *,
        instrument: str,
        as_of: datetime,
        evidence: Sequence[Evidence],
        context: dict[str, Any],
    ) -> RiskAssessment:
        blocker = context.get("blocker")
        return RiskAssessment(
            overall_score=0.8 if blocker else 0.1,
            blockers=(str(blocker),) if blocker else (),
        )


def test_review_engine_runs_multi_instrument_pipeline_and_journals(tmp_path) -> None:
    journal = DecisionJournal(tmp_path / "journal.jsonl")
    engine = AnalystReviewEngine(
        evidence_engine=EvidenceEngine((SignalProvider(),)),
        risk_engine=RiskEngine((TestRiskProvider(),)),
        synthesizer=RuleBasedDecisionSynthesizer(),
        journal=journal,
    )

    session = engine.review(
        instruments=("AAA", "BBB"),
        as_of=NOW,
        context_by_instrument={
            "AAA": {"score": 0.9},
            "BBB": {"score": 1.0, "blocker": "data stale"},
        },
        market_context={"session": "REGULAR"},
    )

    assert session.snapshot.candidates[0].instrument == "AAA"
    assert session.snapshot.candidates[1].instrument == "BBB"
    assert session.snapshot.candidates[1].state.value == "BLOCKED"
    assert len(journal.entries()) == 1


def test_markdown_report_exposes_evidence_risk_and_human_review_boundary(tmp_path) -> None:
    engine = AnalystReviewEngine(
        evidence_engine=EvidenceEngine((SignalProvider(),)),
        risk_engine=RiskEngine((TestRiskProvider(),)),
        synthesizer=RuleBasedDecisionSynthesizer(),
    )
    session = engine.review(
        instruments=("AAA",),
        as_of=NOW,
        context_by_instrument={"AAA": {"score": 0.9}},
        market_context={"regime": "NORMAL"},
    )

    report = render_markdown(session)
    assert "# QuantOs analyst review" in report
    assert "AAA positive signal" in report
    assert "human review only" in report
    assert "regime: NORMAL" in report


@pytest.mark.parametrize("required", [True, False])
def test_review_isolates_future_provider_output_and_journals_required_failure(tmp_path, required):
    class RevisedSignal(SignalProvider):
        name = "revision"

        def collect_evidence(self, **kwargs):
            (valid,) = super().collect_evidence(**kwargs)
            return (valid, replace(valid, available_at=NOW + timedelta(seconds=1), summary="late"))

    journal = DecisionJournal(tmp_path / "review.jsonl")
    engine = AnalystReviewEngine(
        evidence_engine=EvidenceEngine(
            (SignalProvider(), RevisedSignal()), required_providers=("revision",) if required else (),
        ),
        risk_engine=RiskEngine((TestRiskProvider(),)),
        synthesizer=RuleBasedDecisionSynthesizer(), journal=journal,
    )
    session = engine.review(instruments=("X",), as_of=NOW, context_by_instrument={})
    candidate = session.snapshot.candidates[0]
    assert len(candidate.evidence) == 1
    assert session.failures[0].provider == "revision"
    assert candidate.state is (DecisionState.BLOCKED if required else DecisionState.CANDIDATE)
    assert journal.entries()[0]["candidates"][0]["state"] == candidate.state.value
    assert any("revision" in note for note in journal.entries()[0]["notes"])
    if required:
        assert candidate.priority_score == 0
        assert any("revision" in reason for reason in candidate.risk.blockers)
    assert "late" not in [item.summary for item in candidate.evidence]


def test_failed_risk_check_blocks_while_retaining_other_assessments(tmp_path):
    class BrokenRisk:
        name = "exposure"

        def assess(self, **kwargs):
            raise RuntimeError("feed offline")

    journal = DecisionJournal(tmp_path / "review.jsonl")
    engine = AnalystReviewEngine(
        evidence_engine=EvidenceEngine((SignalProvider(),)),
        risk_engine=RiskEngine((BrokenRisk(), TestRiskProvider())),
        synthesizer=RuleBasedDecisionSynthesizer(), journal=journal,
    )
    session = engine.review(
        instruments=("X", "Y"), as_of=NOW, context_by_instrument={"Y": {"blocker": "data stale"}},
    )
    assert all(item.state is DecisionState.BLOCKED for item in session.snapshot.candidates)
    assert all(item.priority_score == 0 for item in session.snapshot.candidates)
    assert "feed offline" in render_markdown(session)
    assert any("exposure" in item for item in journal.entries()[0]["alerts"])
    assert "data stale" in session.snapshot.candidates[1].risk.blockers
