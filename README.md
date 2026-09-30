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

## Current milestone: live bStocks basis dataset

Two collection modes now exist.

One-shot REST scan:

    bstocks-scan --threshold-bps 10

Continuous official WebSocket collection:

    bstocks-stream --symbols SPYBUSDT,NVDABUSDT --duration-seconds 600

The WebSocket collector:

1. dynamically discovers current USDT bStocks;
2. confirms candidates through Binance reference-price calculation type = EXTERNAL;
3. subscribes through Binance official SDK to bookTicker and referencePrice;
4. samples paired best bid/ask and reference state;
5. records basis, executable convergence edge, reference lag and stream event age;
6. appends research observations to data/stream_basis.csv.

No custom WebSocket client is implemented.

## Research definition

Reference-price basis:

    mid = (best_bid + best_ask) / 2
    basis = mid / reference_price - 1

Gross convergence edges:

    long_edge = reference_price / ask - 1
    short_edge = bid / reference_price - 1

These are research measurements, not trading signals. Gross edge is before fees, slippage,
latency and borrow constraints. SHORT remains theoretical until actual margin/borrow availability
is verified.

See:

- docs/research/001-reference-basis.md
- docs/research/002-websocket-collection.md

## Quick start

Python 3.12+ is recommended.

    python -m venv .venv
    source .venv/bin/activate
    pip install -e '.[dev]'
    pytest
    bstocks-scan --no-write
    bstocks-stream --symbols SPYBUSDT,NVDABUSDT --duration-seconds 60

Research data is written below data/ and ignored by Git.

## Codespaces

The repo includes a devcontainer. In GitHub:

    Code -> Codespaces -> Create codespace on main

Dependencies install automatically.

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
