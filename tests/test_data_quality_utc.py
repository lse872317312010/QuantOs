"""Regression tests for actual elapsed time and future data in quality reports."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from quantos.data import DataQualityState, DataSource, assess_data_quality

NY = ZoneInfo("America/New_York")
SOURCE = DataSource(
    source_id="test.book",
    provider="test",
    dataset="book",
    source_type="test",
    expected_interval_s=600.0,
)


@pytest.mark.parametrize(
    ("last", "as_of", "age", "state"),
    [
        (
            datetime(2026, 3, 8, 1, 55, tzinfo=NY),
            datetime(2026, 3, 8, 3, 5, tzinfo=NY),
            600.0,
            DataQualityState.HEALTHY,
        ),
        (
            datetime(2026, 11, 1, 1, 45, tzinfo=NY, fold=0),
            datetime(2026, 11, 1, 1, 16, tzinfo=NY, fold=1),
            1860.0,
            DataQualityState.STALE,
        ),
        (
            datetime(2026, 11, 1, 1, 45, tzinfo=NY, fold=0),
            datetime(2026, 11, 1, 1, 15, tzinfo=NY, fold=1),
            1800.0,
            DataQualityState.HEALTHY,
        ),
        (
            datetime(2026, 10, 31, 23, 55, tzinfo=NY),
            datetime(2026, 11, 1, 0, 5, tzinfo=NY),
            600.0,
            DataQualityState.HEALTHY,
        ),
    ],
)
def test_freshness_uses_elapsed_time(last, as_of, age, state):
    report = assess_data_quality(
        SOURCE, as_of=as_of, last_event_at=last, observed_count=1
    )
    assert report.freshness_s == age
    assert report.state is state
    assert report.as_of.tzinfo is UTC
    assert report.last_event_at.tzinfo is UTC


@pytest.mark.parametrize(
    ("last", "as_of"),
    [
        (
            datetime(2026, 11, 1, 1, 15, tzinfo=NY, fold=1),
            datetime(2026, 11, 1, 1, 45, tzinfo=NY, fold=0),
        ),
        (
            datetime(2026, 11, 1, 12, tzinfo=UTC) + timedelta(seconds=1),
            datetime(2026, 11, 1, 12, tzinfo=UTC),
        ),
    ],
)
def test_future_observation_cannot_report_healthy(last, as_of):
    report = assess_data_quality(
        SOURCE, as_of=as_of, last_event_at=last, observed_count=1,
        expected_count=1,
    )
    assert report.state is DataQualityState.UNAVAILABLE
    assert report.freshness_s is None
    assert report.completeness is None
    assert report.last_event_at is None
    assert "after as_of" in report.issues[0]


def test_same_instant_across_zones_has_zero_age():
    as_of = datetime(2026, 11, 1, 1, 15, tzinfo=NY, fold=1)
    report = assess_data_quality(
        SOURCE, as_of=as_of, last_event_at=as_of.astimezone(UTC), observed_count=1
    )
    assert report.freshness_s == 0
    assert report.state is DataQualityState.HEALTHY


def test_missing_observation_keeps_unavailable_state():
    as_of = datetime(2026, 11, 1, 1, 15, tzinfo=NY, fold=1)
    report = assess_data_quality(
        SOURCE, as_of=as_of, last_event_at=None, observed_count=0
    )
    assert report.state is DataQualityState.UNAVAILABLE
    assert report.as_of.tzinfo is UTC
    assert report.freshness_s is None
