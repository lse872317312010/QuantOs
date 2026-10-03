# Upstream matrix

QuantOs is upstream-first. The core repository should integrate mature libraries and official APIs
rather than reimplement generic infrastructure.

| Capability | Upstream | Policy |
|---|---|---|
| Binance Spot REST / WebSocket | `binance-sdk-spot` | Direct use |
| bStocks reference price / exchangeInfo | Binance official Spot API/SDK | Direct use |
| US-equity trading calendar | `exchange_calendars` / XNYS | Direct use |
| Columnar analytics | Polars | Direct use |
| Local analytical query engine | DuckDB | Direct use |
| Immutable analytical datasets | Parquet / PyArrow | Direct use |
| Statistical primitives | SciPy / NumPy | Direct use |
| Portfolio analysis / walk-forward CV | skfolio | Direct use where applicable |
| Fast research/backtest exploration | VectorBT | Optional research tool |
| Event-driven execution validation | NautilusTrader | Optional downstream validation only |
| Execution-pattern reference | Hummingbot | Reference/reuse only if action adapters are added |

## Platform policy

Generic concerns that should normally come from upstreams:

- exchange authentication and transports;
- calendars;
- dataframe/query engines;
- statistical tests;
- portfolio metrics and optimization;
- generic cross-validation;
- generic backtest/execution engines;
- serialization / API frameworks;
- charting and dashboard primitives.

QuantOs-specific code should concentrate on:

- canonical decision/evidence/risk contracts;
- source normalization adapters;
- market-state semantics;
- evidence provenance;
- risk blockers;
- decision synthesis and ranking;
- cross-domain analytical workflows;
- human-facing explanations and decision history.

## Change rule

Before implementing infrastructure, search official APIs and mature upstream projects first. A new
generic infrastructure module requires an ADR explaining why existing upstream capability is
insufficient.
