from datetime import UTC, datetime
from pathlib import Path

import duckdb

from quantos.data import (
    AnalyticalCatalog,
    DataQualityState,
    DataSource,
    SnapshotBuilder,
    SnapshotSourceQuery,
)


def write_parquet(path: Path, sql: str) -> None:
    con = duckdb.connect()
    try:
        con.execute(f"COPY ({sql}) TO ? (FORMAT PARQUET)", [str(path)])
    finally:
        con.close()


def test_snapshot_builder_combines_two_sources_without_future_leakage(tmp_path: Path) -> None:
    book = tmp_path / "book.parquet"
    reference = tmp_path / "reference.parquet"
    write_parquet(
        book,
        """
        SELECT * FROM (
            VALUES
                ('SPYBUSDT.BINANCE', TIMESTAMPTZ '2026-10-04 00:00:00+00', 100.0, 100.2),
                ('SPYBUSDT.BINANCE', TIMESTAMPTZ '2026-10-04 00:00:03+00', 103.0, 103.2)
        ) AS t(instrument_id, ts_event, bid, ask)
        """,
    )
    write_parquet(
        reference,
        """
        SELECT * FROM (
            VALUES
                ('SPYBUSDT.BINANCE', TIMESTAMPTZ '2026-10-04 00:00:01+00', 100.1),
                ('SPYBUSDT.BINANCE', TIMESTAMPTZ '2026-10-04 00:00:04+00', 104.1)
        ) AS t(instrument_id, ts_event, reference_price)
        """,
    )

    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    catalog.register_source(
        DataSource(
            source_id="binance.book",
            provider="binance",
            dataset="bookTicker",
            source_type="parquet",
            expected_interval_s=5.0,
        ),
        parquet_path=book,
    )
    catalog.register_source(
        DataSource(
            source_id="binance.reference",
            provider="binance",
            dataset="referencePrice",
            source_type="parquet",
            expected_interval_s=5.0,
        ),
        parquet_path=reference,
    )

    snapshot = SnapshotBuilder(catalog).build(
        "SPYBUSDT.BINANCE",
        as_of=datetime(2026, 10, 4, 0, 0, 2, tzinfo=UTC),
        sources=(
            SnapshotSourceQuery(
                source_id="binance.book",
                timestamp_column="ts_event",
                instrument_column="instrument_id",
                value_columns=("bid", "ask"),
                prefix="book_",
            ),
            SnapshotSourceQuery(
                source_id="binance.reference",
                timestamp_column="ts_event",
                instrument_column="instrument_id",
                value_columns=("reference_price",),
            ),
        ),
    )

    assert float(snapshot.values["book_bid"]) == 100.0
    assert float(snapshot.values["book_ask"]) == 100.2
    assert float(snapshot.values["reference_price"]) == 100.1
    assert snapshot.source_ids == ("binance.book", "binance.reference")
    assert all(report.state is DataQualityState.HEALTHY for report in snapshot.quality)


def test_snapshot_builder_marks_unregistered_source_unavailable(tmp_path: Path) -> None:
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    snapshot = SnapshotBuilder(catalog).build(
        "SPYBUSDT.BINANCE",
        as_of=datetime(2026, 10, 4, tzinfo=UTC),
        sources=(
            SnapshotSourceQuery(
                source_id="missing",
                timestamp_column="ts_event",
                instrument_column="instrument_id",
                value_columns=("mid",),
            ),
        ),
    )
    assert snapshot.source_ids == ()
    assert snapshot.quality[0].state is DataQualityState.UNAVAILABLE
