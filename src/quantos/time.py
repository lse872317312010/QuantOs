"""Actual instants shared by analytical contracts and point-in-time queries."""

from datetime import UTC, datetime


def as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)
