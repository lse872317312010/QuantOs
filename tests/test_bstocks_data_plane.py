from datetime import UTC, datetime, timedelta
from pathlib import Path

from bstocks_alpha.data_plane import (
    BOOK_SOURCE_ID,
    REFERENCE_SOURCE_ID,
    register_basis_csv,
)
from quantos.data import (
    AnalyticalCatalog,
    DataQualityState,
    SnapshotBuilder,
    SnapshotSourceQuery,
    catalog_health,
)


def test_basis_csv_registers_two_sources_and_instruments(tmp_path: Path) -> None:
    csv_path = tmp_path / "basis.csv"
    csv_path.write_text(
        "observed_timestamp_ms,symbol,base_asset,inferred_underlying_ticker,bid,ask,mid,"
        "spread_bps,reference_price,reference_timestamp_ms,reference_lag_ms,"
        "external_calculation_id,book_age_ms,reference_receive_age_ms,book_update_id\n"
        "1791072000000,SPYBUSDT,SPY,SPY,100.0,100.2,100.1,19.98,100.15,"
        "1791071999900,100,123,20,30,77\n",
        encoding="utf-8",
    )
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")

    book_path, reference_path = register_basis_csv(
        catalog,
        csv_path,
        output_dir=tmp_path / "parquet",
    )

    assert book_path.exists()
    assert reference_path.exists()
    assert {source.source_id for source in catalog.list_sources()} == {
        BOOK_SOURCE_ID,
        REFERENCE_SOURCE_ID,
    }
    instruments = catalog.list_instruments()
    assert len(instruments) == 1
    assert instruments[0].instrument_id == "SPYBUSDT.BINANCE"
    assert instruments[0].underlying_id == "SPY"


def test_reference_arrivals_and_revisions_replay_only_when_known(tmp_path):
    start = datetime(2026, 11, 1, 5, 59, 59, tzinfo=UTC)
    event = int(start.timestamp() * 1000)
    source = tmp_path / "basis.csv"
    source.write_text(
        "observed_timestamp_ms,symbol,base_asset,inferred_underlying_ticker,bid,ask,mid,"
        "spread_bps,reference_price,reference_timestamp_ms,reference_lag_ms,"
        "external_calculation_id,book_age_ms,reference_receive_age_ms,book_update_id\n"
        f"{event + 1000},SPYBUSDT,SPY,SPY,10,12,11,1,11,{event},1000,1,50,0,3\n"
        f"{event + 2000},SPYBUSDT,SPY,SPY,10,12,11,1,12,{event},2000,1,50,0,4\n"
        f"{event + 3000},SPYBUSDT,SPY,SPY,10,12,11,1,13,{event},3000,1,50,0,5\n"
        f"{event + 3000},SPYBUSDT,SPY,SPY,10,12,11,1,14,{event},3000,1,50,0,6\n"
    )
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    register_basis_csv(catalog, source, output_dir=tmp_path / "parquet")
    spec = SnapshotSourceQuery(REFERENCE_SOURCE_ID, "ts_event", "instrument_id", ("reference_price",))
    builder = SnapshotBuilder(catalog)

    for delay, expected in ((999, None), (1000, 11), (1999, 11), (2000, 12), (3000, 14)):
        cutoff = start + timedelta(milliseconds=delay)
        snapshot = builder.build("SPYBUSDT.BINANCE", as_of=cutoff, sources=(spec,))
        assert snapshot.values.get("reference_price") == expected
        health = {report.source_id: report for report in catalog_health(catalog, as_of=cutoff)}
        assert (health[REFERENCE_SOURCE_ID].state is DataQualityState.UNAVAILABLE) == (expected is None)


def test_ambiguous_legacy_rest_capture_has_no_historical_availability(tmp_path):
    source = tmp_path / "rest.csv"
    source.write_text(
        "observed_timestamp_ms,symbol,base_asset,inferred_underlying_ticker,bid,ask,mid,"
        "spread_bps,reference_price,reference_timestamp_ms,reference_lag_ms,"
        "external_calculation_id,book_age_ms,reference_receive_age_ms,book_update_id\n"
        "1700000001000,X,X,X,10,12,11,1,10,1700000000000,1000,1,0,0,\n"
    )
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    register_basis_csv(catalog, source, output_dir=tmp_path / "parquet")
    reports = catalog_health(catalog, as_of=datetime(2026, 1, 1, tzinfo=UTC))
    assert all(report.state is DataQualityState.UNAVAILABLE for report in reports)
