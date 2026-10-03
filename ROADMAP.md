# QuantOs roadmap

## North-star workflow

A user should be able to open QuantOs and answer:

1. What is happening in the markets I care about?
2. What changed materially since my last review?
3. Which instruments or themes deserve attention?
4. What evidence supports or contradicts each idea?
5. What are the relevant risks and invalidation conditions?
6. How does the idea interact with my existing portfolio?
7. What should I watch next?

The platform should make these answers reproducible and auditable.

## Phase A — platform foundation — current priority

Deliver:
- canonical decision/evidence/risk contracts;
- source/market/research/risk/decision module boundaries;
- data provenance conventions;
- instrument and venue identity model;
- decision snapshot format;
- architecture and contribution rules.

Exit criterion:
new markets and evidence providers can plug in without changing the core contracts.

## Phase B — analytical data plane

Deliver:
- canonical market-event schemas;
- local Parquet + DuckDB catalog;
- ingestion registry and health checks;
- freshness/completeness metrics;
- historical query API;
- unified instrument registry.

Exit criterion:
the platform can answer point-in-time analytical queries across at least two data sources.

## Phase C — evidence plane

Deliver:
- adapt current bStocks research outputs into generic Evidence objects;
- market regime provider;
- liquidity provider;
- anomaly provider;
- strategy/research provider interface;
- evidence provenance and confidence calibration.

Exit criterion:
one instrument can have several independent evidence domains displayed together.

## Phase D — risk and portfolio context

Deliver:
- position/exposure model;
- concentration/correlation views;
- liquidity and event-risk blockers;
- scenario/stress framework;
- portfolio-aware candidate annotations.

Exit criterion:
a strong strategy signal can be downgraded or blocked for explicit portfolio/risk reasons.

## Phase E — decision synthesis

Deliver:
- candidate aggregation and ranking;
- supporting vs contradicting evidence;
- confidence and uncertainty display;
- invalidation conditions;
- alternatives;
- decision snapshots and journal.

Exit criterion:
the system can produce a ranked, explainable decision slate without placing an order.

## Phase F — analyst workspace

Deliver:
- dashboard / API;
- market overview;
- candidate detail;
- evidence tree;
- risk dashboard;
- research explorer;
- alerts;
- decision history.

Exit criterion:
daily market review can be performed primarily inside QuantOs.

## Phase G — optional action adapters

Only after the decision workflow is useful:
- alert delivery;
- paper/shadow execution;
- order-ticket drafts;
- optional broker/exchange handoff.

Autonomous execution is explicitly outside the current priority.
