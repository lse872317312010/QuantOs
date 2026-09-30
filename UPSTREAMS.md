# Upstream matrix

| Capability | Upstream | Policy |
|---|---|---|
| Binance Spot REST / WebSocket | `binance/binance-connector-python` / `binance-sdk-spot` | Direct use |
| bStocks reference price | Binance Spot official API/SDK | Direct use |
| Binance market rules / exchangeInfo | Binance Spot official API/SDK | Direct use |
| Event-driven backtest/live | NautilusTrader | Direct use; no fork by default |
| Execution patterns | Hummingbot | Reuse/reference; separate service if needed |
| bStocks-specific strategy ideas | MINA-BINANCE-AGENTOS | Study/reuse ideas; do not use as production core without independent validation |
| Fast research | VectorBT / Polars | Optional |
| Portfolio optimization / CV | skfolio | Optional |
| Local analytical storage | Parquet + DuckDB | Direct use |

## Change rule

Before implementing infrastructure, search upstream projects and official Binance APIs first. A new infrastructure module requires an ADR explaining why upstream capability is insufficient.
