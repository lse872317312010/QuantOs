# Analytical data plane

## Purpose

The data plane gives every later QuantOs layer a common point-in-time view of market information.
It is intentionally analytical rather than execution-oriented.

## Upstream boundary

QuantOs does not implement a database engine, Parquet reader or full trading-engine instrument
model.

- DuckDB supplies local catalog/query execution.
- Parquet remains the immutable analytical dataset format.
- Exchange/vendor adapters preserve native payloads outside the canonical core.
- Rich trading semantics can map to upstream engines such as NautilusTrader if later required.

The core contract remains thin enough to support non-tradable reference series and future
fundamental/event datasets in addition to market instruments.

## Canonical identity

`Instrument.instrument_id` should be stable within QuantOs. The recommended market convention is:

    {normalized-symbol}.{venue}

The source-native symbol remains available separately as `raw_symbol`.

## Time semantics

Every normalized market event has:

- `ts_event`: when the source says the event occurred;
- `ts_received`: when QuantOs received the event.

Both timestamps must be timezone-aware.

Point-in-time analytical queries use an explicit `as_of` timestamp and only return rows at or
before it.

Both the event clock and the source's availability clock must be at or before that cutoff.
The catalog uses `ts_received` by default. An adapter may name another timezone-aware column
in `DataSource.metadata["availability_column"]`. A local observation can use its event clock
for both only when the producer establishes that the clocks coincide. A source without a
verifiable clock yields an explicit unavailable report. For the same event time the newest
eligible version wins. Sources with same-instant revisions can register a `sequence_column`
to order those versions.

The bStocks adapter uses the completed pair as the availability of derived CSV fields.
The reference event has its vendor timestamp. For bookTicker, the book timestamp is the local
receipt reconstructed from sample time and book age. Sampling an unchanged book preserves
its age. The health report measures quote age. Connection status requires separate telemetry.

### Replaying existing captures

1. Preserve the original CSV, Parquet, research outputs and journal. Register the CSV into
   a fresh catalog and directory, for example
   `bstocks-register-data --input data/stream_basis.csv --catalog data/replay.duckdb --output-dir data/replay`.
2. New collectors stamp `available_timestamp_ms` after both inputs exist. The legacy
   WebSocket collector's non-null `book_update_id` identifies a stream observation that was
   already received at sampling. Old REST batches recorded time before per-symbol responses.
   Rows with neither a verified pair time nor a stream update ID remain archived and
   unavailable for historical decisions. Re-exporting such rows cannot recover their clock.
3. Continue an old stream CSV when its update IDs preserve the timing contract. Start a fresh
   CSV for REST or streams with missing IDs so the explicit availability column can be saved.
   For a mixed archive, keep new captures in a versioned file. The offline research command
   reports the number of unverified or late pairs and the usable observation count in
   `analysis_config.json`.

## Source registry

`AnalyticalCatalog` stores:

- source identity and provider;
- dataset/source type;
- expected update cadence;
- arbitrary source metadata;
- optional registered Parquet path.

It also stores canonical instruments.

The registry is metadata only; DuckDB and Parquet remain the storage/query primitives.

## Quality semantics

`assess_data_quality` produces explicit states:

- `HEALTHY`
- `DEGRADED`
- `STALE`
- `INCOMPLETE`
- `UNAVAILABLE`

Missing observations never become synthetic values. A downstream decision layer should reduce
confidence or block a conclusion when critical sources are stale or unavailable.

## Multi-source snapshots

`SnapshotBuilder` combines the most recent valid row from each configured source at the same
`as_of` timestamp.

Example conceptual view:

    SPYBUSDT.BINANCE @ 10:00:00 UTC
      binance.book        -> bid / ask @ 09:59:59.800
      binance.reference   -> reference @ 09:59:59.500
      quality             -> health per source

Rows after 10:00:00 UTC are invisible to that snapshot.

This is the foundation for regime, evidence, risk and decision synthesis layers.
