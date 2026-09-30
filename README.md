# QuantOs

Research-first repository for Binance bStocks / tokenized-equity alpha. This repo deliberately does **not** implement a trading engine, exchange connector, order state machine, generic backtester, or portfolio optimizer.

## Upstream-first policy

Use mature upstreams for infrastructure:

- Binance official Spot SDK (`binance-sdk-spot`) for Spot REST/WebSocket/streams, including bStocks reference-price endpoints.
- NautilusTrader for event-driven backtest/live execution when we graduate a strategy to execution.
- Hummingbot executors as reusable execution-pattern references (TWAP/grid/DCA/arbitrage) when useful.
- MINA-BINANCE-AGENTOS as a bStocks-specific idea/risk reference, not as the production core.
- VectorBT/skfolio/Polars/DuckDB for research and portfolio analysis as needed.

Our code should concentrate on **features, hypotheses, validation, and strategy logic**.

## First research primitive

Reference-price basis:

```text
basis = token_price / reference_price - 1
```

This is intentionally tiny: the goal is to validate whether the market contains repeatable edge before adding complexity.

## Quick start

Python 3.12+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python examples/binance_reference_price.py SPYBUSDT
```

For NautilusTrader production work, keep the engine as an optional dependency and follow its stable-version guidance. Do not silently move real-capital execution to a pre-release engine.

## Layout

```text
src/bstocks_alpha/       thin Binance access + our alpha features
examples/                executable public-data smoke tests
config/                  research market configuration only
docs/decisions/          architecture decision records
tests/                   feature and policy tests
```

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

See `UPSTREAMS.md` and `docs/decisions/0001-upstream-first.md`.
