# QuantOs

Research-first repository for Binance bStocks / tokenized-equity alpha. This repo deliberately does **not** implement a trading engine, exchange connector, order state machine, generic backtester, or portfolio optimizer.

## Upstream-first policy

Use mature upstreams for infrastructure:

- Binance official Spot SDK (binance-sdk-spot) for Spot REST/WebSocket/streams, including bStocks reference-price endpoints.
- NautilusTrader for event-driven backtest/live execution when we graduate a strategy to execution.
- Hummingbot executors as reusable execution-pattern references when useful.
- MINA-BINANCE-AGENTOS as a bStocks-specific idea/risk reference, not as the production core.
- VectorBT/skfolio/Polars/DuckDB for research and portfolio analysis as needed.

Our code should concentrate on **features, hypotheses, validation, and strategy logic**.

## Current milestone: live bStocks basis scanner

The repository now has a first end-to-end public-data pipeline:

1. Query Binance Spot exchange metadata.
2. Find trading USDT symbols following the bStocks B-suffix naming convention.
3. Confirm each candidate through Binance reference-price calculation type = EXTERNAL.
4. Pull best bid/ask through Binance's official SDK.
5. Pull Binance official reference price.
6. Compute midpoint/reference basis and spread in basis points.
7. Rank anomalies and append snapshots to a local CSV research dataset.

No static bStocks symbol list is required.

## Quick start

Python 3.12+ is recommended.

    python -m venv .venv
    source .venv/bin/activate
    pip install -e '.[dev]'
    pytest
    bstocks-scan --threshold-bps 25

By default snapshots append to:

    data/basis_snapshots.csv

To inspect without writing:

    bstocks-scan --no-write

## Codespaces

The repo includes a devcontainer. In GitHub:

    Code -> Codespaces -> Create codespace on main

Dependencies install automatically.

## Research definition

Reference-price basis:

    mid = (best_bid + best_ask) / 2
    basis = mid / reference_price - 1

This raw basis is not a trading signal by itself. It must survive spread, fees, latency,
underlying-market session effects and out-of-sample validation.

See docs/research/001-reference-basis.md.

## Layout

    src/bstocks_alpha/       thin Binance access + alpha features
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
