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
