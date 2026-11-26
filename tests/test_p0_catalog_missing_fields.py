"""Missing source fields must not erase independent, valid snapshot evidence."""

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
from quantos.data.catalog import SourceAvailabilityError


@pytest.mark.parametrize("missing", ["bid", "instrument_id"])
def test_missing_parquet_field_is_unavailable_without_erasing_other_sources(tmp_path, missing):
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    cutoff = datetime(2026, 11, 25, 10, tzinfo=UTC)
    fields = {
        "ts_event": "TIMESTAMPTZ '2026-11-25 10:00:00+00' AS ts_event",
        "ts_received": "TIMESTAMPTZ '2026-11-25 10:00:00+00' AS ts_received",
        "instrument_id": "'X.BINANCE' AS instrument_id",
        "bid": "99.0 AS bid",
    }
    for source_id in ("broken", "good"):
        parquet = tmp_path / f"{source_id}.parquet"
        projection = ", ".join(
            expr for name, expr in fields.items()
            if source_id == "good" or name != missing
        )
        with duckdb.connect() as con:
            con.execute(f"COPY (SELECT {projection}) TO ? (FORMAT PARQUET)", [str(parquet)])
        catalog.register_source(
            DataSource(source_id, "fixture", "quotes", "market", expected_interval_s=1),
            parquet_path=parquet,
        )

    with pytest.raises(SourceAvailabilityError, match=missing):
        catalog.query_as_of(
            "broken",
            as_of=cutoff,
            timestamp_column="ts_event",
            instrument_column="instrument_id",
            instrument_id="X.BINANCE",
            columns=("bid",),
        )

    snapshot = SnapshotBuilder(catalog).build(
        "X.BINANCE",
        as_of=cutoff,
        sources=(
            SnapshotSourceQuery("broken", "ts_event", "instrument_id", ("bid",), "broken_"),
            SnapshotSourceQuery("good", "ts_event", "instrument_id", ("bid",), "good_"),
        ),
    )
    assert snapshot.values == {"good_bid": 99.0}
    assert snapshot.source_ids == ("good",)
    by_source = {report.source_id: report for report in snapshot.quality}
    assert by_source["broken"].state is DataQualityState.UNAVAILABLE
    assert by_source["broken"].freshness_s is None
    assert missing in by_source["broken"].issues[0]
    assert by_source["good"].state is DataQualityState.HEALTHY
