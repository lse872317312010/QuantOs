"""P0: unusable values must not be presented as healthy point-in-time evidence."""

from datetime import UTC, datetime

import duckdb
import pytest

from quantos.data import (
    AnalyticalCatalog,
    DataQualityState,
    DataSource,
    SnapshotBuilder,
    SnapshotSourceQuery,
)


@pytest.mark.parametrize("bad_value", ["NULL", "'NaN'", "'Infinity'", "'-Infinity'"])
def test_latest_unusable_value_is_not_replaced_by_old_data(tmp_path, bad_value):
    cutoff = datetime(2026, 11, 25, 10, tzinfo=UTC)
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")

    for source_id, current in (("broken", bad_value), ("good", "0")):
        path = tmp_path / f"{source_id}.parquet"
        with duckdb.connect() as con:
            con.execute(
                f"""
                COPY (
                    SELECT *, ts_event AS ts_received FROM (
                        VALUES
                            ('X', TIMESTAMPTZ '2026-11-25 09:59:59+00', 98.0, 99.0),
                            ('X', TIMESTAMPTZ '2026-11-25 10:00:00+00',
                             CAST({current} AS DOUBLE), 100.0)
                    ) AS t(instrument_id, ts_event, bid, ask)
                ) TO ? (FORMAT PARQUET)
                """,
                [str(path)],
            )
        catalog.register_source(
            DataSource(source_id, "fixture", "quotes", "parquet", expected_interval_s=1),
            parquet_path=path,
        )

    specs = tuple(
        SnapshotSourceQuery(key, "ts_event", "instrument_id", ("bid", "ask"), key + "_")
        for key in ("broken", "good")
    )
    snapshot = SnapshotBuilder(catalog).build("X", as_of=cutoff, sources=specs)
    assert snapshot.values == {"good_bid": 0.0, "good_ask": 100.0}
    assert snapshot.source_ids == ("good",)
    reports = {report.source_id: report for report in snapshot.quality}
    assert reports["broken"].state is DataQualityState.UNAVAILABLE
    assert reports["broken"].freshness_s is None
    assert "bid" in reports["broken"].issues[0]
    assert reports["good"].state is DataQualityState.HEALTHY
