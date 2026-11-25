from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta
from importlib.metadata import version
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
    SessionCloseHorizon,
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


@pytest.fixture(scope="module")
def nyse_close():
    return SessionCloseHorizon.from_calendar(
        "XNYS", 1, start=date(2026, 1, 1), end=date(2026, 12, 31),
    )


@pytest.mark.parametrize(("registered", "expected"), [
    ("2026-11-25T20:59:59.999999+00:00", "2026-11-25T21:00:00+00:00"),
    ("2026-11-25T21:00:00+00:00", "2026-11-27T18:00:00+00:00"),
    ("2026-11-26T20:00:00+00:00", "2026-11-27T18:00:00+00:00"),
    ("2026-11-27T17:59:59.999999+00:00", "2026-11-27T18:00:00+00:00"),
    ("2026-11-28T02:00:00+08:00", "2026-11-30T21:00:00+00:00"),
    ("2026-11-28T10:00:00+08:00", "2026-11-30T21:00:00+00:00"),
    ("2026-03-06T21:00:00+00:00", "2026-03-09T20:00:00+00:00"),
    ("2026-10-30T20:00:00+00:00", "2026-11-02T21:00:00+00:00"),
])
def test_session_horizon_counts_strictly_future_closes(nyse_close, registered, expected):
    result = nyse_close.target_after(datetime.fromisoformat(registered))
    assert result.tzinfo is UTC
    assert result == datetime.fromisoformat(expected)


def test_session_forecast_uses_registration_time_and_waits_for_its_actual_label(nyse_close):
    registered = datetime(2026, 11, 25, 21, tzinfo=UTC)
    rule = replace(nyse_close, sessions=2)
    h = hypothesis(horizon_seconds=None, session_horizon=rule)
    target = rule.target_after(registered)
    assert target == datetime(2026, 11, 30, 21, tzinfo=UTC)
    with pytest.raises(ValueError, match="horizon"):
        forecast(hypothesis=h, registered_at=registered, target_end=registered + timedelta(days=2))
    f = forecast(hypothesis=h, registered_at=registered, target_end=target)
    o = outcome(target_end=target, available_at=target + timedelta(minutes=10))
    premature = registered + timedelta(days=2)
    assert scoring_status(f, o, as_of=premature) is ScoringStatus.PENDING_HORIZON
    assert scoring_status(f, None, as_of=target) is ScoringStatus.PENDING_OUTCOME
    assert scoring_status(f, o, as_of=target) is ScoringStatus.PENDING_AVAILABILITY
    assert scoring_status(f, o, as_of=o.available_at) is ScoringStatus.READY


def test_session_calendar_versions_and_coverage_fail_closed(nyse_close, monkeypatch):
    assert nyse_close.calendar_version == version("exchange_calendars")
    assert nyse_close.calendar_name == "XNYS"
    t = datetime(2026, 11, 26, 12, tzinfo=UTC)
    target = nyse_close.target_after(t)
    h = hypothesis(horizon_seconds=None, session_horizon=nyse_close)
    f = forecast(hypothesis=h, registered_at=t, target_end=target)
    for late in (datetime(2026, 12, 31, 21, tzinfo=UTC), datetime(2025, 12, 30, tzinfo=UTC)):
        with pytest.raises(ValueError, match="coverage"):
            nyse_close.target_after(late)
    with pytest.raises(ValueError, match="coverage"):
        replace(nyse_close, sessions=300).target_after(t)
    with pytest.raises(ValueError, match="version"):
        replace(nyse_close, calendar_version="unavailable-version").target_after(t)
    with pytest.raises(ValueError, match="timezone-aware"):
        nyse_close.target_after(t.replace(tzinfo=None))

    def changed_schedule(*args):
        raise AssertionError("scoring attempted to resolve a frozen deadline")

    monkeypatch.setattr(SessionCloseHorizon, "target_after", changed_schedule)
    matured = outcome(target_end=target, available_at=target)
    assert scoring_status(f, matured, as_of=target) is ScoringStatus.READY


def test_session_horizon_cannot_override_an_elapsed_contract(nyse_close):
    assert hypothesis().horizon_seconds == 3600
    with pytest.raises(ValueError, match="horizon"):
        hypothesis(session_horizon=nyse_close)
    with pytest.raises(ValueError, match="horizon"):
        hypothesis(horizon_seconds=None)
    with pytest.raises(ValueError, match="horizon"):
        hypothesis(horizon_seconds=None, session_horizon="XNYS")
    for invalid in (True, 0, -1, 1.5):
        with pytest.raises(ValueError, match="sessions"):
            replace(nyse_close, sessions=invalid)


def test_calendar_window_starting_on_a_holiday_or_at_an_overnight_open():
    rule = SessionCloseHorizon.from_calendar(
        "XNYS", 1, start=date(2026, 11, 26), end=date(2026, 11, 30),
    )
    thanksgiving = datetime(2026, 11, 26, 15, tzinfo=UTC)
    assert rule.target_after(thanksgiving) == datetime(2026, 11, 27, 18, tzinfo=UTC)
    with pytest.raises(ValueError, match="coverage"):
        rule.target_after(datetime(2026, 11, 25, 17, tzinfo=UTC))

    all_days = SessionCloseHorizon.from_calendar(
        "24/7", 1, start=date(2026, 11, 26), end=date(2026, 11, 30),
    )
    first_open = datetime(2026, 11, 26, tzinfo=UTC)
    assert all_days.target_after(first_open) == first_open + timedelta(days=1)


def test_default_calendar_window_is_captured_and_reproducible():
    rule = SessionCloseHorizon.from_calendar("XNYS", 1)
    middle_day = rule.schedule_start + (rule.schedule_end - rule.schedule_start) // 2
    instant = datetime.combine(middle_day, datetime.min.time(), tzinfo=UTC)
    explicit = SessionCloseHorizon.from_calendar(
        "XNYS", 1, start=rule.schedule_start, end=rule.schedule_end,
    )
    assert explicit == rule
    assert explicit.target_after(instant) == rule.target_after(instant)


def test_calendar_alias_is_canonical_and_unknown_venue_has_no_fallback():
    from exchange_calendars.errors import InvalidCalendarName

    start, end = date(2026, 11, 25), date(2026, 11, 30)
    assert SessionCloseHorizon.from_calendar("NYSE", 1, start=start, end=end).calendar_name == "XNYS"
    with pytest.raises(InvalidCalendarName):
        SessionCloseHorizon.from_calendar("UNKNOWN-TEST-VENUE", 1, start=start, end=end)
