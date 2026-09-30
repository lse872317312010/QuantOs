# QuantOs

Research-first repository for Binance bStocks / tokenized-equity alpha. This repo deliberately does **not** implement a trading engine, exchange connector, order state machine, generic backtester, or portfolio optimizer.

## Upstream-first policy

Use mature upstreams for infrastructure:

- Binance official Spot SDK for Spot REST/WebSocket/streams and bStocks reference-price endpoints.
- exchange_calendars / XNYS for US-equity holidays and actual regular-session boundaries.
- NautilusTrader for event-driven backtest/live execution when a strategy graduates to execution.
- Hummingbot executors as reusable execution-pattern references when useful.
- VectorBT/skfolio/Polars/DuckDB for research and portfolio analysis as needed.

Our code concentrates on features, hypotheses, validation and strategy logic.

## Current research pipeline

### 1. One-shot market scan

    bstocks-scan --threshold-bps 10

### 2. Continuous official WebSocket collection

    bstocks-stream --symbols SPYBUSDT,NVDABUSDT --duration-seconds 600

The collector dynamically discovers current USDT bStocks, subscribes through Binance official SDK
to bookTicker and referencePrice, pairs the latest states and records basis, executable convergence
edge and timing freshness.

### 3. Forward-outcome research

Install research dependencies and analyze collected observations:

    pip install -e '.[research]'
    bstocks-analyze --input data/stream_basis.csv

Default horizons are 1s, 5s, 30s and 5m. The analysis:

1. rejects stale local stream state by configurable event age;
2. labels PRE / REGULAR / AFTER / CLOSED using XNYS sessions;
3. forward-matches the first same-symbol observation near each requested horizon;
4. calculates executable entry-to-exit returns using ask-to-future-bid for LONG and
   bid-to-future-ask for SHORT;
5. measures absolute basis convergence;
6. summarizes results by horizon, market session, freshness, edge bucket and side.

Outputs:

    data/research/signals.parquet
    data/research/forward_outcomes.parquet
    data/research/forward_summary.csv

These are research measurements, not trading signals. Gross edge and forward returns remain before
fees, slippage, financing and verified short-borrow availability.

See:

- docs/research/001-reference-basis.md
- docs/research/002-websocket-collection.md
- docs/research/003-forward-outcomes.md

## Quick start

Python 3.12+ is recommended.

    python -m venv .venv
    source .venv/bin/activate
    pip install -e '.[dev,research]'
    pytest
    bstocks-scan --no-write
    bstocks-stream --symbols SPYBUSDT,NVDABUSDT --duration-seconds 60
    bstocks-analyze --input data/stream_basis.csv

Research data is written below data/ and ignored by Git.

## Codespaces

The repo includes a devcontainer. In GitHub:

    Code -> Codespaces -> Create codespace on main

Dependencies install automatically.

## Layout

    src/bstocks_alpha/       thin Binance access + alpha/research features
    config/                  research market configuration only
    docs/decisions/          architecture decision records
    docs/research/           explicit research hypotheses and validation plans
    tests/                   unit/policy tests

## Non-goals

Do not add custom implementations of:

- exchange authentication / signing
- REST/WebSocket transport
- matching engine
- order lifecycle / OMS
- generic event bus
- generic backtest engine
- generic portfolio optimizer
- performance metric library

If an upstream lacks one bStocks-specific field, add the thinnest possible adapter and prefer contributing it upstream.

## Upstreams

See UPSTREAMS.md and docs/decisions/0001-upstream-first.md.
