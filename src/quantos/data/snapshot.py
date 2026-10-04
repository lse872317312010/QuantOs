"""Point-in-time snapshot assembly across registered analytical sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .catalog import AnalyticalCatalog
from .models import DataQualityReport, DataSource, MarketSnapshot
from .quality import assess_data_quality


@dataclass(frozen=True, slots=True)
class SnapshotSourceQuery:
    """How one registered source contributes fields to an analytical snapshot."""

    source_id: str
    timestamp_column: str
    instrument_column: str
    value_columns: tuple[str, ...]
    prefix: str = ""


class SnapshotBuilder:
    """Assemble reproducible as-of views without looking beyond the requested timestamp."""

    def __init__(self, catalog: AnalyticalCatalog) -> None:
        self.catalog = catalog

    def build(
        self,
        instrument_id: str,
        *,
        as_of: datetime,
        sources: tuple[SnapshotSourceQuery, ...],
    ) -> MarketSnapshot:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        values: dict[str, Any] = {}
        quality_reports: list[DataQualityReport] = []
        used_sources: list[str] = []

        for spec in sources:
            source = self.catalog.get_source(spec.source_id)
            if source is None:
                quality_reports.append(
                    self._missing_source_report(spec.source_id, as_of)
                )
                continue

            rows = self.catalog.query_as_of(
                spec.source_id,
                as_of=as_of,
                timestamp_column=spec.timestamp_column,
                instrument_column=spec.instrument_column,
                instrument_id=instrument_id,
                columns=(spec.timestamp_column, *spec.value_columns),
                limit=1,
            )
            if not rows:
                quality_reports.append(
                    assess_data_quality(
                        source,
                        as_of=as_of,
                        last_event_at=None,
                        observed_count=0,
                    )
                )
                continue

            row = rows[0]
            event_time = row[spec.timestamp_column]
            for column in spec.value_columns:
                values[f"{spec.prefix}{column}"] = row[column]

            quality_reports.append(
                assess_data_quality(
                    source,
                    as_of=as_of,
                    last_event_at=event_time,
                    observed_count=1,
                )
            )
            used_sources.append(spec.source_id)

        return MarketSnapshot(
            instrument_id=instrument_id,
            as_of=as_of,
            values=values,
            source_ids=tuple(used_sources),
            quality=tuple(quality_reports),
        )

    @staticmethod
    def _missing_source_report(source_id: str, as_of: datetime) -> DataQualityReport:
        placeholder = DataSource(
            source_id=source_id,
            provider="unknown",
            dataset="unregistered",
            source_type="unknown",
        )
        return assess_data_quality(
            placeholder,
            as_of=as_of,
            last_event_at=None,
            observed_count=0,
        )
