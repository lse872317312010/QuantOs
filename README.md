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

    pip install -e '.[research]'
    bstocks-analyze --input data/stream_basis.csv

Default horizons are 1s, 5s, 30s and 5m. The analysis rejects stale stream state, labels US-equity
sessions, forward-matches same-symbol observations, crosses entry/exit spreads, and measures basis
convergence.

### 4. Cost sensitivity + chronological holdout

The same command now applies configurable costs and a date-level holdout:

    bstocks-analyze \
      --input data/stream_basis.csv \
      --taker-fee-bps-per-side 10 \
      --slippage-bps-per-side 2 \
      --test-fraction 0.30

The default fee baseline is 10 bps per taker side, matching the Binance regular-user standard Spot
taker rate observed on 2026-09-30. Override it for actual VIP/BNB/promotion/account conditions.
Spread is already embedded in executable forward returns and is not deducted twice.

Outputs:

    data/research/signals.parquet
    data/research/forward_outcomes.parquet
    data/research/forward_summary.csv
    data/research/holdout_summary.csv
    data/research/analysis_config.json

The forward outcome dataset includes gross and net return, cost components, New York market date,
and TRAIN/TEST sample labels. If fewer than two market dates exist, the sample is labeled UNSPLIT.

### 5. Date-clustered uncertainty

High-frequency rows from one day are not treated as independent experiments. The pipeline first
collapses net returns to market-date clusters and then runs a deterministic date bootstrap:

    bstocks-analyze \
      --input data/stream_basis.csv \
      --bootstrap-resamples 2000 \
      --bootstrap-min-dates 5

Additional outputs:

    data/research/daily_net_summary.csv
    data/research/bootstrap_ci.csv

Confidence intervals are left null when a research cell has too few independent market dates.

### 6. Threshold stability + multiple-testing control

Candidate thresholds are screened on TRAIN dates only. Daily means are tested with SciPy and
Benjamini-Hochberg FDR correction; TEST metrics remain descriptive and cannot change the selection
flags.

    bstocks-analyze \
      --input data/stream_basis.csv \
      --thresholds-bps 5,10,15,25,50 \
      --threshold-min-train-dates 5 \
      --fdr-alpha 0.05

Additional output:

    data/research/threshold_stability.csv

A stable TRAIN candidate must pass FDR and have at least one adjacent threshold pass as well.

These are research measurements, not trading signals.

See:

- docs/research/001-reference-basis.md
- docs/research/002-websocket-collection.md
- docs/research/003-forward-outcomes.md
- docs/research/004-costs-and-oos.md
- docs/research/005-date-cluster-bootstrap.md
- docs/research/006-threshold-stability-fdr.md

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
