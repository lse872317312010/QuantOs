# QuantOs

QuantOs is a **human-in-the-loop market analysis and decision-support platform**.

The system is designed to help a person answer:

- what is happening in the market;
- what changed materially;
- which instruments or themes deserve attention;
- what evidence supports or contradicts an idea;
- what risks, blockers and invalidation conditions matter;
- how an idea interacts with portfolio context;
- what should be watched next.

QuantOs may rank, compare, warn and explain. **The human remains the final decision-maker.**
Automatic order submission and autonomous capital allocation are not the product priority.

## Architecture

The platform is organized around a decision pipeline:

    source connectors
        -> canonical data / storage
        -> market state / features
        -> research and model evidence
        -> regime / risk / portfolio context
        -> decision synthesis
        -> analyst workspace / alerts
        -> human decision
        -> optional downstream action adapter

The core output is not an order. It is an auditable decision snapshot containing evidence,
confidence, risk, alternatives and timestamps.

See:

- `docs/architecture/system-platform.md`
- `docs/decisions/0002-human-in-the-loop-platform.md`
- `ROADMAP.md`

## Core packages

    src/quantos/             platform core
    src/quantos/data/        analytical data plane: identity, provenance, quality, as-of queries
    src/bstocks_alpha/       first market + research vertical: Binance bStocks

The `bstocks_alpha` package is intentionally a **provider**, not the platform boundary. Future
markets, research models, risk providers and portfolio providers should plug into the generic
QuantOs contracts.

## Analytical data plane

QuantOs now includes the first platform-wide data layer:

- canonical `Instrument`, `DataSource`, `MarketEvent` and `MarketSnapshot` contracts;
- explicit event-time vs receive-time semantics;
- DuckDB-backed source and instrument registry;
- registered Parquet datasets rather than a custom storage engine;
- freshness/completeness quality reports;
- point-in-time `query_as_of` semantics;
- multi-source snapshot assembly with no future-data leakage;
- a bStocks adapter that splits the existing paired collection into independently registered book
  and reference-price Parquet sources.

Register an existing collection with:

    bstocks-register-data --input data/stream_basis.csv

The catalog is intentionally local-first and lightweight. It can later be replaced or supplemented
by larger infrastructure without changing the analytical contracts.

## Current implemented vertical slice

The first complete vertical slice is Binance bStocks / tokenized-equity basis research.

It currently provides:

1. official Binance market discovery and WebSocket collection;
2. book/reference-price basis features;
3. executable forward-return research;
4. cost sensitivity and chronological holdout;
5. date-clustered bootstrap uncertainty;
6. threshold stability and Benjamini-Hochberg FDR control;
7. repeated walk-forward out-of-sample validation;
8. machine-readable research promotion states.

This subsystem produces research evidence that will be adapted into the generic decision platform.

### Quick research run

    python -m venv .venv
    source .venv/bin/activate
    pip install -e '.[dev,research]'

    bstocks-scan --no-write
    bstocks-stream --symbols SPYBUSDT,NVDABUSDT --duration-seconds 60
    bstocks-analyze --input data/stream_basis.csv

Important outputs include:

    data/research/forward_outcomes.parquet
    data/research/bootstrap_ci.csv
    data/research/threshold_stability.csv
    data/research/walk_forward_summary.csv
    data/research/promotion_gate.csv

These are evidence artifacts, not trading instructions.

## Platform priorities

Current priority is **framework breadth before execution depth**. Phase A (platform contracts and
boundaries) is complete; Phase B (analytical data plane) is now active.

The build order is:

1. core contracts and architecture;
2. analytical data plane and provenance;
3. multi-domain evidence providers;
4. risk and portfolio context;
5. candidate synthesis / ranking / explanation;
6. analyst workspace, alerts and decision history;
7. optional action adapters.

See `ROADMAP.md` for detailed exit criteria.

## Design rules

- upstream-first: do not rebuild mature infrastructure;
- point-in-time correctness: no future-data leakage;
- evidence provenance: every conclusion must be traceable;
- risk can veto: blockers are first-class outputs;
- missing data reduces confidence instead of creating false certainty;
- modular monolith first, services only when scale or isolation requires them;
- no core module may require order execution to be useful.

## Non-goals for the core

Do not implement custom versions of:

- exchange authentication/signing;
- generic REST/WebSocket transports;
- matching engines;
- OMS/order lifecycle;
- generic event buses;
- generic backtest engines;
- generic portfolio optimizers;
- performance metric libraries.

If an upstream lacks one market-specific field, add the thinnest adapter possible.

## Development

Python 3.12+ is recommended.

    pip install -e '.[dev,research-core]'
    ruff check .
    pytest -q

The repository includes a Codespaces devcontainer.

## Documentation

Architecture:

- `docs/architecture/system-platform.md`

Architecture decisions:

- `docs/decisions/0001-upstream-first.md`
- `docs/decisions/0002-human-in-the-loop-platform.md`

Current research vertical:

- `docs/research/001-reference-basis.md`
- `docs/research/002-websocket-collection.md`
- `docs/research/003-forward-outcomes.md`
- `docs/research/004-costs-and-oos.md`
- `docs/research/005-date-cluster-bootstrap.md`
- `docs/research/006-threshold-stability-fdr.md`
- `docs/research/007-walk-forward-oos.md`
- `docs/research/008-research-promotion-gates.md`
