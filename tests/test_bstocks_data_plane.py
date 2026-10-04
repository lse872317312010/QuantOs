from pathlib import Path

from bstocks_alpha.data_plane import (
    BOOK_SOURCE_ID,
    REFERENCE_SOURCE_ID,
    register_basis_csv,
)
from quantos.data import AnalyticalCatalog


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
