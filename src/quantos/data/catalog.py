"""DuckDB-backed local analytical catalog for source, instrument and Parquet metadata."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from .models import DataSource, Instrument

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SourceAvailabilityError(ValueError):
    """The source lacks a verifiable clock for point-in-time queries."""


@dataclass(frozen=True, slots=True)
class RegisteredSource:
    source: DataSource
    parquet_path: str | None


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
    def connection(
        self, existing: duckdb.DuckDBPyConnection | None = None,
    ) -> Iterator[duckdb.DuckDBPyConnection]:
        if existing is not None:
            yield existing
            return
        con = duckdb.connect(self.path)
        try:
            con.execute("SET TimeZone = 'UTC'")
            yield con
        finally:
            con.close()

    @contextmanager
    def transaction(self) -> Iterator[duckdb.DuckDBPyConnection]:
        """Close without committing if any registration fails."""
        with self.connection() as con:
            con.begin()
            yield con
            con.commit()

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

    def register_source(
        self, source: DataSource, *, parquet_path: str | Path | None = None,
        connection: duckdb.DuckDBPyConnection | None = None,
    ) -> None:
        with self.connection(connection) as con:
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

    def register_instrument(
        self, instrument: Instrument, *, connection: duckdb.DuckDBPyConnection | None = None,
    ) -> None:
        with self.connection(connection) as con:
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
        entry = self.registered_sources((source_id,)).get(source_id)
        return entry.source if entry else None

    def list_sources(self) -> list[DataSource]:
        return [entry.source for entry in self.registered_sources().values()]

    def registered_sources(
        self, source_ids: tuple[str, ...] | None = None,
    ) -> dict[str, RegisteredSource]:
        """Read the dataset paths and clocks for a whole report in one registry query."""
        where = "" if source_ids is None else "WHERE source_id = ANY(?::VARCHAR[])"
        with self.connection() as con:
            rows = con.execute(
                f"""
                SELECT source_id, provider, dataset, source_type, expected_interval_s,
                       description, metadata_json, parquet_path
                FROM quantos_sources {where} ORDER BY source_id
                """,
                [] if source_ids is None else [list(source_ids)],
            ).fetchall()
        return {
            row[0]: RegisteredSource(
                source=DataSource(
                    source_id=row[0], provider=row[1], dataset=row[2], source_type=row[3],
                    expected_interval_s=row[4], description=row[5], metadata=json.loads(row[6]),
                ),
                parquet_path=row[7],
            )
            for row in rows
        }

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
        registration: RegisteredSource | None = None,
    ) -> list[dict[str, Any]]:
        """Return the latest event versions already available by the requested instant."""
        if as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        as_of = as_of.astimezone(UTC)
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

        if registration is None:
            registration = self.registered_sources((source_id,)).get(source_id)
        if registration is None or registration.parquet_path is None:
            raise KeyError(f"source has no registered parquet dataset: {source_id}")
        if registration.source.source_id != source_id:
            raise ValueError("registration belongs to a different source")
        parquet_path = registration.parquet_path
        metadata = registration.source.metadata
        with self.connection() as con:
            availability = metadata.get("availability_column", "ts_received")
            sequence = metadata.get("sequence_column")
            self._require_identifier(availability)
            try:
                fields = con.execute("DESCRIBE SELECT * FROM read_parquet(?)", [parquet_path]).fetchall()
            except (duckdb.IOException, duckdb.InvalidInputException) as exc:
                raise SourceAvailabilityError(f"{source_id} cannot open its Parquet dataset") from exc
            schema = {row[0]: row[1] for row in fields}
            for clock in (timestamp_column, availability):
                if schema.get(clock) != "TIMESTAMP WITH TIME ZONE":
                    raise SourceAvailabilityError(
                        f"{source_id} needs a timezone-aware {clock} column for point-in-time reads"
                    )
            # A source with a changed schema is unavailable for this projection,
            # not a reason to discard other sources in the same snapshot.
            required = set(columns or ())
            if instrument_id is not None:
                required.add(instrument_column)
            missing = sorted(required.difference(schema))
            if missing:
                raise SourceAvailabilityError(
                    f"{source_id} is missing requested fields: {', '.join(missing)}"
                )
            order = [f"{timestamp_column} DESC", f"{availability} DESC"]
            if sequence is not None:
                self._require_identifier(sequence)
                if sequence not in schema:
                    raise SourceAvailabilityError(f"{source_id} is missing revision sequence {sequence}")
                order.append(f"{sequence} DESC NULLS LAST")

            where = [f"{timestamp_column} <= ?", f"{availability} <= ?"]
            params: list[Any] = [parquet_path, as_of, as_of]
            if instrument_id is not None:
                where.append(f"{instrument_column} = ?")
                params.append(instrument_id)
            params.append(limit)
            query = f"""
                SELECT {projection} FROM read_parquet(?)
                WHERE {" AND ".join(where)}
                ORDER BY {", ".join(order)} LIMIT ?
            """
            result = con.execute(query, params)
            names = [description[0] for description in result.description]
            return [dict(zip(names, row, strict=True)) for row in result.fetchall()]

    @staticmethod
    def _require_identifier(value: str) -> None:
        if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
            raise ValueError(f"invalid column identifier: {value}")
