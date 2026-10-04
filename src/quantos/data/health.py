"""Catalog-wide source health reporting."""

from __future__ import annotations

from datetime import datetime

from .catalog import AnalyticalCatalog
from .models import DataQualityReport
from .quality import assess_data_quality


def catalog_health(
    catalog: AnalyticalCatalog,
    *,
    as_of: datetime,
) -> list[DataQualityReport]:
    """Assess freshness for every registered source with a Parquet dataset."""
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    reports: list[DataQualityReport] = []
    for source in catalog.list_sources():
        parquet_path = catalog.source_parquet_path(source.source_id)
        if parquet_path is None:
            reports.append(
                assess_data_quality(
                    source,
                    as_of=as_of,
                    last_event_at=None,
                    observed_count=0,
                )
            )
            continue

        timestamp_column = str(source.metadata.get("timestamp_column", "ts_event"))
        rows = catalog.query_as_of(
            source.source_id,
            as_of=as_of,
            timestamp_column=timestamp_column,
            columns=(timestamp_column,),
            limit=1,
        )
        last_event_at = rows[0][timestamp_column] if rows else None
        reports.append(
            assess_data_quality(
                source,
                as_of=as_of,
                last_event_at=last_event_at,
                observed_count=1 if rows else 0,
            )
        )
    return reports
