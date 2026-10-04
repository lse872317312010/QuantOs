"""Data freshness and completeness assessment."""

from __future__ import annotations

from datetime import datetime

from .models import DataQualityReport, DataQualityState, DataSource


def assess_data_quality(
    source: DataSource,
    *,
    as_of: datetime,
    last_event_at: datetime | None,
    observed_count: int,
    expected_count: int | None = None,
    stale_after_intervals: float = 3.0,
) -> DataQualityReport:
    """Assess a source without inventing data when observations are missing."""
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if last_event_at is not None and last_event_at.tzinfo is None:
        raise ValueError("last_event_at must be timezone-aware")
    if observed_count < 0:
        raise ValueError("observed_count must be non-negative")
    if expected_count is not None and expected_count < 0:
        raise ValueError("expected_count must be non-negative")
    if stale_after_intervals <= 0:
        raise ValueError("stale_after_intervals must be positive")

    completeness = None
    if expected_count is not None:
        completeness = 1.0 if expected_count == 0 else min(1.0, observed_count / expected_count)

    if last_event_at is None:
        return DataQualityReport(
            source_id=source.source_id,
            as_of=as_of,
            state=DataQualityState.UNAVAILABLE,
            freshness_s=None,
            completeness=completeness,
            issues=("no observations",),
        )

    freshness_s = max(0.0, (as_of - last_event_at).total_seconds())
    issues: list[str] = []

    stale_limit = None
    if source.expected_interval_s is not None:
        stale_limit = source.expected_interval_s * stale_after_intervals

    if stale_limit is not None and freshness_s > stale_limit:
        state = DataQualityState.STALE
        issues.append(f"freshness {freshness_s:.3f}s exceeds {stale_limit:.3f}s")
    elif completeness is not None and completeness < 1.0:
        state = DataQualityState.INCOMPLETE
        issues.append(f"completeness {completeness:.3f} below 1.0")
    else:
        state = DataQualityState.HEALTHY

    return DataQualityReport(
        source_id=source.source_id,
        as_of=as_of,
        state=state,
        freshness_s=freshness_s,
        completeness=completeness,
        last_event_at=last_event_at,
        issues=tuple(issues),
    )
