"""Adapter from existing bStocks basis datasets into the generic QuantOs data plane."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from quantos.data import AnalyticalCatalog, DataSource, Instrument

BOOK_SOURCE_ID = "binance.bstocks.book"
REFERENCE_SOURCE_ID = "binance.bstocks.reference"


def register_basis_csv(
    catalog: AnalyticalCatalog,
    csv_path: str | Path,
    *,
    output_dir: str | Path = "data/catalog/bstocks",
) -> tuple[Path, Path]:
    """Split the current paired research CSV into canonical book/reference Parquet sources."""
    source = Path(csv_path)
    if not source.exists():
        raise FileNotFoundError(source)

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    book_path = target / "book.parquet"
    reference_path = target / "reference.parquet"

    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TEMP VIEW basis AS
            SELECT
                *,
                symbol || '.BINANCE' AS instrument_id,
                to_timestamp(observed_timestamp_ms / 1000.0) AS ts_observed,
                to_timestamp(reference_timestamp_ms / 1000.0) AS ts_reference
            FROM read_csv_auto(?, header = true)
            """,
            [str(source)],
        )
        con.execute(
            """
            COPY (
                SELECT
                    instrument_id,
                    ts_observed AS ts_event,
                    bid,
                    ask,
                    mid,
                    spread_bps,
                    book_age_ms,
                    book_update_id
                FROM basis
                ORDER BY ts_observed, instrument_id
            ) TO ? (FORMAT PARQUET)
            """,
            [str(book_path)],
        )
        con.execute(
            """
            COPY (
                SELECT
                    instrument_id,
                    ts_reference AS ts_event,
                    reference_price,
                    reference_lag_ms,
                    reference_receive_age_ms,
                    external_calculation_id
                FROM basis
                ORDER BY ts_reference, instrument_id
            ) TO ? (FORMAT PARQUET)
            """,
            [str(reference_path)],
        )
        instruments = con.execute(
            """
            SELECT DISTINCT
                instrument_id,
                symbol,
                base_asset,
                inferred_underlying_ticker
            FROM basis
            ORDER BY instrument_id
            """
        ).fetchall()
    finally:
        con.close()

    for instrument_id, symbol, base_asset, underlying in instruments:
        catalog.register_instrument(
            Instrument(
                instrument_id=instrument_id,
                symbol=symbol,
                raw_symbol=symbol,
                venue="BINANCE",
                asset_class="TOKENIZED_EQUITY",
                base_currency=base_asset,
                quote_currency="USDT",
                underlying_id=underlying,
                metadata={"provider_domain": "bstocks"},
            )
        )

    catalog.register_source(
        DataSource(
            source_id=BOOK_SOURCE_ID,
            provider="binance",
            dataset="bstocks_book",
            source_type="parquet",
            expected_interval_s=1.0,
            description="Best bid/ask observations extracted from paired bStocks collection.",
        ),
        parquet_path=book_path,
    )
    catalog.register_source(
        DataSource(
            source_id=REFERENCE_SOURCE_ID,
            provider="binance",
            dataset="bstocks_reference_price",
            source_type="parquet",
            expected_interval_s=1.0,
            description="Reference-price observations extracted from paired bStocks collection.",
        ),
        parquet_path=reference_path,
    )
    return book_path, reference_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Register an existing bStocks basis CSV in the QuantOs analytical catalog"
    )
    parser.add_argument("--input", default="data/stream_basis.csv")
    parser.add_argument("--catalog", default="data/quantos.duckdb")
    parser.add_argument("--output-dir", default="data/catalog/bstocks")
    return parser


def main() -> None:
    args = _parser().parse_args()
    catalog = AnalyticalCatalog(args.catalog)
    book_path, reference_path = register_basis_csv(
        catalog,
        args.input,
        output_dir=args.output_dir,
    )
    print(f"registered {BOOK_SOURCE_ID}: {book_path}")
    print(f"registered {REFERENCE_SOURCE_ID}: {reference_path}")
    print(f"instruments={len(catalog.list_instruments())}")


if __name__ == "__main__":
    main()
