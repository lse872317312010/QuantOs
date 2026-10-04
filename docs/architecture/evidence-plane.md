# Evidence plane

## Purpose

The evidence plane converts raw analytical state into small, auditable claims that can later be
combined by risk and decision-synthesis layers.

An Evidence object is not an order and is not, by itself, a recommendation.

## Provider boundary

Every provider implements the platform `EvidenceProvider` protocol:

    instrument + as_of + context -> Sequence[Evidence]

Providers should be narrow. Examples:

- data quality;
- liquidity;
- market regime;
- anomaly detection;
- one research model;
- one fundamental or event source.

`EvidenceEngine` executes providers independently. A provider exception is returned as an
`EvidenceFailure`; valid evidence from other providers remains available.

## Current domains

The platform currently supports:

- MARKET
- MICROSTRUCTURE
- STRATEGY
- REGIME
- RISK
- LIQUIDITY
- FUNDAMENTAL
- EVENT
- ANOMALY
- DATA_QUALITY
- PORTFOLIO

## Confidence

`confidence` is the provider's confidence that its own evidence is reliable, from 0 to 1. It is
not a probability that a trade will profit.

Examples:

- stale/unavailable data reduces data-dependent evidence confidence;
- a validated research gate can carry higher confidence than an unvalidated signal;
- an anomaly provider may scale confidence with anomaly magnitude.

Calibration against realized outcomes remains a separate roadmap item.

## Directional score

`directional_score` lies in [-1, 1]:

- positive: evidence favors upside/long direction;
- negative: evidence favors downside/short direction;
- zero: non-directional context, including liquidity, data quality and many regime facts.

The decision layer should never treat a high absolute score as sufficient without risk/context.

## bStocks vertical

The current bStocks vertical contributes two generic evidence providers:

1. `BStocksBasisEvidenceProvider` turns the current book/reference snapshot into microstructure
   evidence and an executable convergence direction.
2. `BStocksResearchGateEvidenceProvider` reads the Research 008 promotion table and attaches the
   applicable historical validation state as STRATEGY evidence.

This keeps "current opportunity" separate from "historical model evidence" while allowing them to
appear together in the same human-facing decision view.
