# ADR-0001: Upstream-first infrastructure

## Status
Accepted

## Context
The project begins with Binance bStocks and may later expand to crypto, equities, futures, options, and additional venues. Rebuilding generic trading infrastructure creates maintenance risk without creating alpha.

## Decision
1. Binance official APIs/SDKs are authoritative for Binance protocol semantics and bStocks reference-price data.
2. NautilusTrader is the preferred event-driven backtest/live engine. Do not fork it by default.
3. Hummingbot execution components are evaluated before writing custom TWAP/grid/DCA/arbitrage executors.
4. MINA-BINANCE-AGENTOS is a source of bStocks-specific research/risk ideas, not the production core.
5. Project-owned code focuses on features, signals, experiments, validation, and thin adapters for genuinely missing bStocks fields.
6. Any new generic infrastructure requires a new ADR proving no suitable upstream exists.

## Consequences
The repository stays small. Alpha code is portable. Upstream version changes must be tracked explicitly, but protocol and engine maintenance stay with the projects that specialize in them.
