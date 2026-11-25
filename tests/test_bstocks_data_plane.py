from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import pytest

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


CAPTURE_MS = 1_791_072_000_000
CAPTURE_HEADER = (
    "observed_timestamp_ms,symbol,base_asset,inferred_underlying_ticker,bid,ask,mid,"
    "spread_bps,reference_price,reference_timestamp_ms,reference_lag_ms,"
    "external_calculation_id,book_age_ms,reference_receive_age_ms,book_update_id"
)


def write_capture(path, price, delay=0, header=CAPTURE_HEADER):
    timestamp = CAPTURE_MS + delay
    path.write_text(
        f"{header}\n"
        f"{timestamp},X,X,X,{price},{price + 2},{price + 1},1,{price + 1},"
        f"{timestamp},0,1,0,0,7\n"
    )


def test_failed_second_export_preserves_both_previous_files(tmp_path):
    path = tmp_path / "capture.csv"
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    output = tmp_path / "parquet"
    write_capture(path, 10)
    previous = register_basis_csv(catalog, path, output_dir=output)
    before = [p.read_bytes() for p in previous]
    write_capture(path, 20, header=CAPTURE_HEADER.replace("reference_price,", "missing_price,"))
    with pytest.raises(duckdb.BinderException):
        register_basis_csv(catalog, path, output_dir=output)
    assert [p.read_bytes() for p in previous] == before
    assert [catalog.source_parquet_path(s) for s in (BOOK_SOURCE_ID, REFERENCE_SOURCE_ID)] == [
        str(p) for p in previous
    ]


def test_registry_failure_rolls_back_and_retry_reuses_verified_files(tmp_path, monkeypatch):
    path = tmp_path / "capture.csv"
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    output = tmp_path / "parquet"
    write_capture(path, 10)
    previous = register_basis_csv(catalog, path, output_dir=output)
    before = [p.read_bytes() for p in previous]
    write_capture(path, 30, delay=1000)
    register = catalog.register_source

    def fail_second(source, **kwargs):
        if source.source_id == REFERENCE_SOURCE_ID:
            raise RuntimeError("injected registry failure")
        register(source, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(catalog, "register_source", fail_second)
        with pytest.raises(RuntimeError, match="injected"):
            register_basis_csv(catalog, path, output_dir=output)
    reopened = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    assert [reopened.source_parquet_path(s) for s in (BOOK_SOURCE_ID, REFERENCE_SOURCE_ID)] == [
        str(p) for p in previous
    ]
    current = register_basis_csv(reopened, path, output_dir=output)
    assert current != previous
    assert register_basis_csv(reopened, path, output_dir=output) == current
    assert [p.read_bytes() for p in previous] == before


@pytest.mark.parametrize("report", ["snapshot", "health"])
def test_import_during_multi_source_read_is_visible_only_on_next_report(tmp_path, monkeypatch, report):
    path = tmp_path / "capture.csv"
    catalog = AnalyticalCatalog(tmp_path / "catalog.duckdb")
    output = tmp_path / "parquet"
    write_capture(path, 10)
    register_basis_csv(catalog, path, output_dir=output)
    write_capture(path, 20, delay=1000)
    query = catalog.query_as_of
    calls = 0

    def interleaved_query(*args, **kwargs):
        nonlocal calls
        rows = query(*args, **kwargs)
        calls += 1
        if calls == 1:
            register_basis_csv(catalog, path, output_dir=output)
        return rows

    monkeypatch.setattr(catalog, "query_as_of", interleaved_query)
    cutoff = datetime.fromtimestamp(CAPTURE_MS / 1000 + 3, UTC)
    if report == "snapshot":
        specs = (
            SnapshotSourceQuery(BOOK_SOURCE_ID, "ts_event", "instrument_id", ("bid",)),
            SnapshotSourceQuery(REFERENCE_SOURCE_ID, "ts_event", "instrument_id", ("reference_price",)),
        )
        builder = SnapshotBuilder(catalog)
        first = builder.build("X.BINANCE", as_of=cutoff, sources=specs)
        second = builder.build("X.BINANCE", as_of=cutoff, sources=specs)
        assert first.values == {"bid": 10, "reference_price": 11}
        assert second.values == {"bid": 20, "reference_price": 21}
    else:
        assert [row.freshness_s for row in catalog_health(catalog, as_of=cutoff)] == [3, 3]
        assert [row.freshness_s for row in catalog_health(catalog, as_of=cutoff)] == [2, 2]
