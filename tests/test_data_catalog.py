from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest

from quantos.data import AnalyticalCatalog, DataSource, Instrument


def make_parquet(path: Path) -> None:
    con = duckdb.connect()
    try:
        con.execute(
            """
            COPY (
                SELECT * FROM (
                    VALUES
                        ('SPYBUSDT.BINANCE', TIMESTAMPTZ '2026-10-04 00:00:00+00', 100.0),
                        ('SPYBUSDT.BINANCE', TIMESTAMPTZ '2026-10-04 00:00:02+00', 101.0),
                        ('NVDABUSDT.BINANCE', TIMESTAMPTZ '2026-10-04 00:00:01+00', 200.0)
                ) AS t(instrument_id, ts_event, mid)
            ) TO ? (FORMAT PARQUET)
            """,
            [str(path)],
        )
    finally:
        con.close()


def test_catalog_registers_sources_and_instruments(tmp_path: Path) -> None:
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    source = DataSource(
        source_id="binance.book",
        provider="binance",
        dataset="bookTicker",
        source_type="websocket",
        expected_interval_s=1.0,
    )
    instrument = Instrument(
        instrument_id="SPYBUSDT.BINANCE",
        symbol="SPYBUSDT",
        venue="BINANCE",
        asset_class="TOKENIZED_EQUITY",
    )

    catalog.register_source(source)
    catalog.register_instrument(instrument)

    assert catalog.get_source("binance.book") == source
    assert catalog.list_instruments() == [instrument]


def test_catalog_queries_point_in_time_parquet(tmp_path: Path) -> None:
    parquet = tmp_path / "quotes.parquet"
    make_parquet(parquet)
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    catalog.register_source(
        DataSource(
            source_id="binance.book",
            provider="binance",
            dataset="bookTicker",
            source_type="parquet",
        ),
        parquet_path=parquet,
    )

    rows = catalog.query_as_of(
        "binance.book",
        as_of=datetime(2026, 10, 4, 0, 0, 1, 500_000, tzinfo=UTC),
        timestamp_column="ts_event",
        instrument_column="instrument_id",
        instrument_id="SPYBUSDT.BINANCE",
        columns=("instrument_id", "ts_event", "mid"),
    )

    assert len(rows) == 1
    assert rows[0]["mid"] == pytest.approx(100.0)


def test_catalog_rejects_dynamic_sql_identifiers(tmp_path: Path) -> None:
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    with pytest.raises(ValueError, match="invalid column identifier"):
        catalog.query_as_of(
            "missing",
            as_of=datetime(2026, 10, 4, tzinfo=UTC),
            timestamp_column="ts_event; DROP TABLE x",
        )
