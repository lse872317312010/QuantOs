from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from quantos.learning import (
    EvidenceLink,
    EvidenceRole,
    ForecastRegistration,
    HypothesisSpec,
    KnowledgeKind,
    OutcomeObservation,
    ScoringStatus,
    scoring_status,
)

T = datetime(2026, 1, 1, 12, tzinfo=UTC)


def link(**changes):
    values = {
        "evidence_id": "ev-1",
        "source_uri": "https://example.org/filing",
        "source_family": "issuer-filing-1",
        "content_sha256": "a" * 64,
        "published_at": T - timedelta(hours=1),
        "first_seen_at": T,
        "recorded_at": T,
        "kind": KnowledgeKind.OBSERVATION,
        "role": EvidenceRole.SUPPORTS,
    }
    return EvidenceLink(**(values | changes))


def hypothesis(**changes):
    values = {
        "hypothesis_id": "h-1",
        "version": 1,
        "registered_at": T,
        "claim": "A synthetic test claim",
        "mechanism": "A testable mechanism, not proven causation",
        "instruments": ("TEST:ASSET",),
        "horizon_seconds": 3600,
        "signal_definition": "Compare with a frozen baseline",
        "benchmark": "No-change baseline",
        "falsification_rule": "No out-of-sample improvement",
        "counterarguments": ("The information may already be priced in",),
        "evidence": (link(),),
    }
    return HypothesisSpec(**(values | changes))


def forecast(**changes):
    values = {
        "forecast_id": "f-1",
        "hypothesis": hypothesis(),
        "registered_at": T,
        "target_end": T + timedelta(hours=1),
        "event_definition": "Return exceeds the fixed benchmark",
        "probability": 0.6,
    }
    return ForecastRegistration(**(values | changes))


def outcome(**changes):
    values = {
        "forecast_id": "f-1",
        "target_end": T + timedelta(hours=1),
        "available_at": T + timedelta(hours=1, minutes=1),
        "occurred": False,
        "source_uri": "dataset://quotes/v1",
        "dataset_version": "quotes-v1",
    }
    return OutcomeObservation(**(values | changes))


@pytest.mark.parametrize("field", ["published_at", "first_seen_at", "recorded_at"])
def test_naive_time_rejected(field):
    with pytest.raises(ValueError, match="timezone-aware"):
        link(**{field: T.replace(tzinfo=None)})


def test_backfilled_or_later_interpreted_evidence_is_not_historical_knowledge():
    later = T + timedelta(days=1)
    with pytest.raises(ValueError, match="unavailable"):
        hypothesis(evidence=(link(first_seen_at=later, recorded_at=later),))
    with pytest.raises(ValueError, match="unavailable"):
        hypothesis(evidence=(link(recorded_at=later, kind=KnowledgeKind.INTERPRETATION),))


def test_future_published_evidence_is_not_available_yet():
    with pytest.raises(ValueError, match="unavailable"):
        hypothesis(evidence=(link(published_at=T + timedelta(minutes=1)),))


def test_duplicates_do_not_create_independent_confirmations():
    h = hypothesis(evidence=(link(), link(evidence_id="ev-2")))
    assert h.source_family_count == 1
    with pytest.raises(ValueError, match="duplicate"):
        hypothesis(evidence=(link(), link()))


@pytest.mark.parametrize("changes", [
    {"benchmark": ""}, {"falsification_rule": ""}, {"counterarguments": ()},
    {"version": 0}, {"horizon_seconds": 0}, {"horizon_seconds": True},
    {"evidence": ()}, {"instruments": ()}, {"instruments": ["mutable"]},
])
def test_incomplete_hypotheses_rejected(changes):
    with pytest.raises(ValueError):
        hypothesis(**changes)


@pytest.mark.parametrize("probability", [float("nan"), float("inf"), -0.1, 1.1, True])
def test_invalid_probability_rejected(probability):
    with pytest.raises(ValueError):
        forecast(probability=probability)


def test_forecast_is_immutable_and_horizon_cannot_drift():
    f = forecast()
    with pytest.raises(FrozenInstanceError):
        f.probability = 0.9
    with pytest.raises(ValueError, match="horizon"):
        forecast(target_end=T + timedelta(minutes=30))


def test_no_early_or_missing_or_unavailable_label_is_scored():
    f, o = forecast(), outcome()
    assert scoring_status(f, o, as_of=T) is ScoringStatus.PENDING_HORIZON
    assert scoring_status(f, None, as_of=f.target_end) is ScoringStatus.PENDING_OUTCOME
    assert scoring_status(f, o, as_of=f.target_end) is ScoringStatus.PENDING_AVAILABILITY
    assert scoring_status(f, o, as_of=o.available_at) is ScoringStatus.READY


def test_mismatched_forecast_or_window_cannot_be_scored():
    with pytest.raises(ValueError, match="does not belong"):
        scoring_status(forecast(), outcome(forecast_id="other"), as_of=T)
    with pytest.raises(ValueError, match="does not belong"):
        scoring_status(
            forecast(), outcome(target_end=T + timedelta(minutes=30)), as_of=T,
        )


def test_outcome_requires_finalization_and_version():
    with pytest.raises(ValueError, match="window closes"):
        outcome(available_at=T)
    with pytest.raises(ValueError, match="boolean"):
        outcome(occurred=1)
    with pytest.raises(ValueError, match="blank"):
        outcome(dataset_version="")


def test_contradictions_are_kept_not_removed():
    contradiction = link(evidence_id="ev-negative", role=EvidenceRole.CONTRADICTS)
    h = hypothesis(evidence=(link(), contradiction))
    assert h.evidence[1].role is EvidenceRole.CONTRADICTS
    assert replace(h, version=2).version == 2
    assert h.version == 1


NY = ZoneInfo("America/New_York")


def test_spring_forward_uses_elapsed_seconds_and_stores_utc():
    start = datetime(2026, 3, 8, 1, 30, tzinfo=NY)
    end = datetime(2026, 3, 8, 3, 30, tzinfo=NY)
    h = hypothesis(registered_at=start)
    f = forecast(hypothesis=h, registered_at=start, target_end=end)
    assert h.registered_at == datetime(2026, 3, 8, 6, 30, tzinfo=UTC)
    assert f.registered_at.tzinfo is UTC
    assert f.target_end == datetime(2026, 3, 8, 7, 30, tzinfo=UTC)
    assert f.target_end - f.registered_at == timedelta(hours=1)
    with pytest.raises(ValueError, match="horizon"):
        forecast(
            hypothesis=replace(h, horizon_seconds=7200),
            registered_at=start,
            target_end=end,
        )


def test_fall_back_does_not_admit_premature_labels():
    start = datetime(2026, 11, 1, 1, 30, tzinfo=NY, fold=0)
    end = datetime(2026, 11, 1, 1, 30, tzinfo=NY, fold=1)
    early = datetime(2026, 11, 1, 1, 45, tzinfo=NY, fold=0)
    f = forecast(hypothesis=hypothesis(registered_at=start), registered_at=start, target_end=end)
    assert f.target_end - f.registered_at == timedelta(hours=1)
    with pytest.raises(ValueError, match="window closes"):
        outcome(target_end=end, available_at=early)
    o = outcome(target_end=end, available_at=end)
    assert o.target_end.tzinfo is UTC
    assert o.available_at.tzinfo is UTC
    assert scoring_status(f, o, as_of=early) is ScoringStatus.PENDING_HORIZON
    assert scoring_status(f, o, as_of=end) is ScoringStatus.READY


def test_repeated_hour_evidence_availability_is_ordered_by_actual_instant():
    early = datetime(2026, 11, 1, 1, 45, tzinfo=NY, fold=0)
    late = datetime(2026, 11, 1, 1, 15, tzinfo=NY, fold=1)
    ev = link(published_at=early, first_seen_at=early, recorded_at=late)
    assert ev.published_at.tzinfo is UTC
    assert ev.first_seen_at.tzinfo is UTC
    assert ev.recorded_at.tzinfo is UTC
    assert ev.available_at == datetime(2026, 11, 1, 6, 15, tzinfo=UTC)
    with pytest.raises(ValueError, match="unavailable"):
        hypothesis(registered_at=early, evidence=(ev,))
    assert hypothesis(registered_at=late, evidence=(ev,)).registered_at == ev.available_at
    with pytest.raises(ValueError, match="recorded_at"):
        link(published_at=early, first_seen_at=late, recorded_at=early)


def test_repeated_hour_forecast_cannot_precede_hypothesis():
    early = datetime(2026, 11, 1, 1, 45, tzinfo=NY, fold=0)
    late = datetime(2026, 11, 1, 1, 15, tzinfo=NY, fold=1)
    h = hypothesis(registered_at=late)
    with pytest.raises(ValueError, match="precede"):
        forecast(hypothesis=h, registered_at=early, target_end=late + timedelta(hours=1))


def test_outcome_window_matches_instant_not_repeated_wall_time():
    start = datetime(2026, 11, 1, 1, 30, tzinfo=NY, fold=0)
    end = datetime(2026, 11, 1, 1, 30, tzinfo=NY, fold=1)
    f = forecast(hypothesis=hypothesis(registered_at=start), registered_at=start, target_end=end)
    wrong = outcome(target_end=start, available_at=end)
    with pytest.raises(ValueError, match="does not belong"):
        scoring_status(f, wrong, as_of=end)


def test_cross_midnight_and_late_extraction_use_actual_availability():
    start = datetime(2026, 1, 2, 23, 30, tzinfo=NY)
    end = datetime(2026, 1, 3, 0, 30, tzinfo=NY)
    ev = link(published_at=start, first_seen_at=start, recorded_at=end)
    with pytest.raises(ValueError, match="unavailable"):
        hypothesis(registered_at=start, evidence=(ev,))
    f = forecast(hypothesis=hypothesis(registered_at=start), registered_at=start, target_end=end)
    o = outcome(target_end=end, available_at=end + timedelta(minutes=1))
    assert scoring_status(f, o, as_of=end) is ScoringStatus.PENDING_AVAILABILITY
    assert scoring_status(f, o, as_of=o.available_at) is ScoringStatus.READY


def test_revision_does_not_replace_original_available_evidence():
    received = datetime(2026, 1, 2, 23, 30, tzinfo=NY)
    original = link(published_at=received, first_seen_at=received, recorded_at=received)
    h = hypothesis(registered_at=received, evidence=(original,))
    revision = replace(
        original,
        content_sha256="b" * 64,
        recorded_at=received + timedelta(hours=1),
    )
    with pytest.raises(ValueError, match="unavailable"):
        replace(h, version=2, evidence=(revision,))
    assert h.evidence[0].content_sha256 == "a" * 64
