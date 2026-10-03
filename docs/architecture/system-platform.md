# QuantOs system architecture — decision-support platform

## Product definition

QuantOs is a **human-in-the-loop market analysis and decision-support platform**.

Its primary job is not to place orders. Its primary job is to continuously transform heterogeneous
market information into an auditable decision view:

    raw data
        -> normalized market state
        -> features and research evidence
        -> regime / risk / portfolio context
        -> ranked decision candidates
        -> explanation, alternatives and alerts
        -> human decision

Execution, when present, is downstream and optional. The architecture must remain useful even when
no broker or exchange account is connected.

## Design principles

1. **Decision-first, not strategy-first.** A strategy is one evidence source among many.
2. **Human authority.** The platform may rank, compare, warn and explain; the human owns the action.
3. **Evidence provenance.** Every candidate must be traceable to timestamped evidence and assumptions.
4. **Risk can veto.** Risk blockers are first-class outputs, not an afterthought.
5. **Multiple markets.** Binance bStocks is the first vertical slice, not the platform boundary.
6. **Upstream-first.** Reuse mature data, statistical, portfolio and execution libraries.
7. **Point-in-time correctness.** Research and decision views must avoid future-data leakage.
8. **Degrade gracefully.** Missing data reduces confidence or blocks a candidate; it should not invent certainty.

## Logical layers

### L0 — Source connectors

Purpose: acquire raw public/account data without embedding strategy logic.

Examples:
- Binance Spot/bStocks market data
- future exchanges or brokers
- reference-price feeds
- economic/event/news feeds
- user portfolio/account state

Policy: official SDKs and mature connectors first.

### L1 — Canonical data and storage

Purpose: normalize heterogeneous feeds into stable, timestamped schemas.

Core concepts:
- instrument identity
- venue
- quotes/trades/order book
- reference price
- session/calendar
- event timestamps and receive timestamps
- portfolio positions
- source provenance

Preferred storage:
- Parquet for immutable research datasets
- DuckDB for local analytical queries
- later: a time-series/OLAP store only when scale requires it

### L2 — Market state and feature services

Purpose: turn normalized data into reusable state, not final decisions.

Examples:
- basis / spread / depth
- volatility and liquidity
- momentum / reversal
- cross-asset relationships
- reference-price freshness
- session state
- anomaly flags

### L3 — Research and model evidence

Purpose: test whether a signal or model is useful and quantify uncertainty.

Current bStocks work already implements:
- executable forward outcomes
- cost sensitivity
- chronological OOS
- date-cluster bootstrap
- FDR / threshold stability
- walk-forward validation
- promotion gates

These outputs become one evidence provider to the decision layer.

### L4 — Regime, risk and portfolio context

Purpose: answer whether an otherwise attractive idea is appropriate **now** and **for this user**.

Subdomains:
- market regime
- instrument liquidity
- exposure / concentration
- correlation / crowding
- event risk
- model/data quality risk
- scenario and stress analysis

Risk produces both scores and hard blockers.

### L5 — Decision synthesis

Purpose: combine independent evidence into candidates for human review.

Canonical output:
- instrument
- stance: favor long / favor short / neutral / avoid / watch
- state: observe / investigate / candidate / blocked
- thesis
- horizon
- confidence
- evidence bundle with provenance
- risk assessment
- alternatives / invalidation conditions
- timestamp

This layer must not contain order submission.

### L6 — Decision workspace / presentation

Purpose: make the system useful to a human.

Views should include:
- market overview
- watchlist and ranked opportunities
- candidate detail / evidence tree
- risk dashboard
- strategy research notebook/results
- scenario comparison
- alerts and anomalies
- portfolio context
- decision journal and historical snapshots

Initial UI may be CLI/reports; web UI comes after contracts stabilize.

### L7 — Optional action adapters

Purpose: export a human-approved decision to downstream workflows.

Examples:
- create an order ticket draft
- send an alert
- open a broker page
- paper/shadow execution
- later, guarded execution

This layer is deliberately outside the core decision loop.

## Deployment shape

Start as a modular monolith:

    quantos core contracts
    + market adapters
    + research services
    + risk/context services
    + decision synthesis
    + local analytical store
    + API/CLI/UI

Split into services only when operational scale or isolation requirements justify it.

## Current vertical slice

The existing `bstocks_alpha` package is retained as the first domain implementation:

    Binance bStocks source
      -> reference basis features
      -> statistical research evidence
      -> promotion status

Next work should expose those outputs through the generic QuantOs evidence/candidate contracts,
rather than extending the bStocks package toward a complete trading engine.
