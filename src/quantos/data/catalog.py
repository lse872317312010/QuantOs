"""DuckDB-backed local analytical catalog for source, instrument and Parquet metadata."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from .models import DataSource, Instrument

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class AnalyticalCatalog:
    """Small local catalog; DuckDB supplies the query/storage engine."""

    def __init__(self, path: str | Path = "data/quantos.duckdb") -> None:
        self.path = str(path)
        parent = Path(self.path).parent
        if self.path != ":memory:":
            parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as con:
            self._ensure_schema(con)

    @contextmanager
    def connection(self) -> Iterator[duckdb.DuckDBPyConnection]:
        con = duckdb.connect(self.path)
        try:
            yield con
        finally:
            con.close()

    @staticmethod
    def _ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS quantos_sources (
                source_id VARCHAR PRIMARY KEY,
                provider VARCHAR NOT NULL,
                dataset VARCHAR NOT NULL,
                source_type VARCHAR NOT NULL,
                expected_interval_s DOUBLE,
                description VARCHAR NOT NULL,
                metadata_json VARCHAR NOT NULL,
                parquet_path VARCHAR
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS quantos_instruments (
                instrument_id VARCHAR PRIMARY KEY,
                symbol VARCHAR NOT NULL,
                venue VARCHAR NOT NULL,
                asset_class VARCHAR NOT NULL,
                quote_currency VARCHAR,
                base_currency VARCHAR,
                underlying_id VARCHAR,
                raw_symbol VARCHAR,
                metadata_json VARCHAR NOT NULL
            )
            """
        )

    def register_source(self, source: DataSource, *, parquet_path: str | Path | None = None) -> None:
        with self.connection() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO quantos_sources VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    source.source_id,
                    source.provider,
                    source.dataset,
                    source.source_type,
                    source.expected_interval_s,
                    source.description,
                    json.dumps(source.metadata, sort_keys=True),
                    str(parquet_path) if parquet_path is not None else None,
                ],
            )

    def register_instrument(self, instrument: Instrument) -> None:
        with self.connection() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO quantos_instruments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    instrument.instrument_id,
                    instrument.symbol,
                    instrument.venue,
                    instrument.asset_class,
                    instrument.quote_currency,
                    instrument.base_currency,
                    instrument.underlying_id,
                    instrument.raw_symbol,
                    json.dumps(instrument.metadata, sort_keys=True),
                ],
            )

    def get_source(self, source_id: str) -> DataSource | None:
        with self.connection() as con:
            row = con.execute(
                """
                SELECT source_id, provider, dataset, source_type, expected_interval_s,
                       description, metadata_json
                FROM quantos_sources WHERE source_id = ?
                """,
                [source_id],
            ).fetchone()
        if row is None:
            return None
        return DataSource(
            source_id=row[0],
            provider=row[1],
            dataset=row[2],
            source_type=row[3],
            expected_interval_s=row[4],
            description=row[5],
            metadata=json.loads(row[6]),
        )

    def list_sources(self) -> list[DataSource]:
        with self.connection() as con:
            rows = con.execute(
                """
                SELECT source_id, provider, dataset, source_type, expected_interval_s,
                       description, metadata_json
                FROM quantos_sources ORDER BY source_id
                """
            ).fetchall()
        return [
            DataSource(
                source_id=row[0],
                provider=row[1],
                dataset=row[2],
                source_type=row[3],
                expected_interval_s=row[4],
                description=row[5],
                metadata=json.loads(row[6]),
            )
            for row in rows
        ]

    def list_instruments(self) -> list[Instrument]:
        with self.connection() as con:
            rows = con.execute(
                """
                SELECT instrument_id, symbol, venue, asset_class, quote_currency, base_currency,
                       underlying_id, raw_symbol, metadata_json
                FROM quantos_instruments ORDER BY instrument_id
                """
            ).fetchall()
        return [
            Instrument(
                instrument_id=row[0],
                symbol=row[1],
                venue=row[2],
                asset_class=row[3],
                quote_currency=row[4],
                base_currency=row[5],
                underlying_id=row[6],
                raw_symbol=row[7],
                metadata=json.loads(row[8]),
            )
            for row in rows
        ]

    def source_parquet_path(self, source_id: str) -> str | None:
        with self.connection() as con:
            row = con.execute(
                "SELECT parquet_path FROM quantos_sources WHERE source_id = ?",
                [source_id],
            ).fetchone()
        return None if row is None else row[0]

    def query_as_of(
        self,
        source_id: str,
        *,
        as_of: datetime,
        timestamp_column: str,
        instrument_column: str | None = None,
        instrument_id: str | None = None,
        columns: tuple[str, ...] | None = None,
        limit: int = 1,
    ) -> list[dict[str, Any]]:
        """Return latest rows at or before an as-of timestamp from registered Parquet data."""
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        if limit < 1:
            raise ValueError("limit must be positive")
        self._require_identifier(timestamp_column)
        if instrument_column is not None:
            self._require_identifier(instrument_column)
        if instrument_id is not None and instrument_column is None:
            raise ValueError("instrument_column is required when instrument_id is supplied")

        projection = "*"
        if columns:
            for column in columns:
                self._require_identifier(column)
            projection = ", ".join(columns)

        parquet_path = self.source_parquet_path(source_id)
        if parquet_path is None:
            raise KeyError(f"source has no registered parquet dataset: {source_id}")

        where = [f"{timestamp_column} <= ?"]
        params: list[Any] = [parquet_path, as_of]
        if instrument_id is not None:
            where.append(f"{instrument_column} = ?")
            params.append(instrument_id)
        params.append(limit)

        query = f"""
            SELECT {projection}
            FROM read_parquet(?)
            WHERE {" AND ".join(where)}
            ORDER BY {timestamp_column} DESC
            LIMIT ?
        """
        with self.connection() as con:
            result = con.execute(query, params)
            names = [description[0] for description in result.description]
            return [dict(zip(names, row, strict=True)) for row in result.fetchall()]

    @staticmethod
    def _require_identifier(value: str) -> None:
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError(f"invalid column identifier: {value}")
