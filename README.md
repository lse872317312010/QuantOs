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

The repository has an end-to-end public-data pipeline:

1. Query Binance Spot exchange metadata.
2. Find trading USDT symbols following the bStocks B-suffix naming convention.
3. Confirm each candidate through Binance reference-price calculation type = EXTERNAL.
4. Pull best bid/ask through Binance official SDK.
5. Pull Binance official reference price.
6. Compute midpoint/reference basis, spread, reference lag and bid/ask-side convergence edge.
7. Rank gross executable convergence edges and append snapshots to a local CSV research dataset.

No static bStocks symbol list is required.

## Quick start

Python 3.12+ is recommended.

    python -m venv .venv
    source .venv/bin/activate
    pip install -e '.[dev]'
    pytest
    bstocks-scan --threshold-bps 10

By default snapshots append to:

    data/basis_snapshots.csv

To inspect without writing:

    bstocks-scan --no-write

The displayed gross edge is before fees, slippage, latency and borrow constraints. SHORT is a
research-side calculation until actual borrow/margin availability is verified.

## Codespaces

The repo includes a devcontainer. In GitHub:

    Code -> Codespaces -> Create codespace on main

Dependencies install automatically.

## Research definition

Reference-price basis:

    mid = (best_bid + best_ask) / 2
    basis = mid / reference_price - 1

Gross convergence edges:

    long_edge = reference_price / ask - 1
    short_edge = bid / reference_price - 1

This is still not a trading signal. It must survive fees, latency, market-session effects,
borrow constraints and out-of-sample validation.

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
