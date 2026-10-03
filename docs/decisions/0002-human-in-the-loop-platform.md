# ADR 0002 — QuantOs is a human-in-the-loop decision-support platform

## Status

Accepted.

## Context

The repository began as a research-first Binance bStocks alpha lab. That was useful for proving
data collection and statistical validation, but it risks making one strategy and eventual automated
execution the center of the product.

The intended system is broader: a platform that helps a human understand markets, compare evidence,
assess risk, identify opportunities and make better decisions across multiple markets.

## Decision

QuantOs is defined as a **system analysis and decision-support platform**.

The core platform will own:
- canonical analytical contracts;
- evidence provenance;
- market-state aggregation;
- research evidence;
- regime/risk/portfolio context;
- decision synthesis;
- alerts, comparison and explanation;
- historical decision snapshots.

The core platform will **not** own:
- automatic order submission;
- autonomous capital allocation;
- exchange-specific OMS logic;
- broker/exchange transport implementations.

Those capabilities, if ever added, are optional downstream adapters and require explicit human
approval boundaries.

The existing `bstocks_alpha` code becomes the first market/research vertical and an evidence
provider, not the product architecture.

## Consequences

Positive:
- architecture can expand to other markets and strategies;
- research results become reusable evidence rather than terminal outputs;
- risk and portfolio context become first-class;
- UI/API design can focus on decision workflows;
- automated execution is no longer a prerequisite for usefulness.

Trade-offs:
- we must define canonical cross-domain contracts early;
- ranking/synthesis logic needs explicit provenance and uncertainty handling;
- some strategy-specific outputs require adapters before they fit the generic platform.
