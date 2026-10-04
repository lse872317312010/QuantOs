from datetime import UTC, datetime
from pathlib import Path

import duckdb

from quantos.data import AnalyticalCatalog, DataQualityState, DataSource, catalog_health


def test_catalog_health_reports_latest_registered_parquet_event(tmp_path: Path) -> None:
    parquet = tmp_path / "source.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            """
            COPY (
                SELECT TIMESTAMPTZ '2026-10-04 00:00:00+00' AS ts_event, 1.0 AS value
            ) TO ? (FORMAT PARQUET)
            """,
            [str(parquet)],
        )
    finally:
        con.close()

    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    catalog.register_source(
        DataSource(
            source_id="example",
            provider="test",
            dataset="example",
            source_type="parquet",
            expected_interval_s=10.0,
            metadata={"timestamp_column": "ts_event"},
        ),
        parquet_path=parquet,
    )

    reports = catalog_health(
        catalog,
        as_of=datetime(2026, 10, 4, 0, 0, 5, tzinfo=UTC),
    )
    assert len(reports) == 1
    assert reports[0].state is DataQualityState.HEALTHY
    assert reports[0].freshness_s == 5.0
