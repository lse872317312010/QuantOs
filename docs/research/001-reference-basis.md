# Research 001 — bStocks reference-price basis

## Question

Does the difference between the Binance bStock market price and Binance official reference price
contain repeatable, executable information after spread, fees, latency and session regime?

## Primitive

We store best bid/ask, midpoint, spread and official reference price.

    mid = (best_bid + best_ask) / 2
    basis_bps = (mid / reference_price - 1) * 10_000
    spread_bps = (best_ask - best_bid) / mid * 10_000

We also compute gross bid/ask-side convergence edges:

    long_convergence_bps = (reference_price / best_ask - 1) * 10_000
    short_convergence_bps = (best_bid / reference_price - 1) * 10_000
    gross_convergence_edge_bps = max(long_convergence_bps, short_convergence_bps)

The long metric crosses the current ask before assuming convergence to reference. The short metric
crosses the current bid but is only theoretical until borrow/margin availability is validated.

We store:

    reference_lag_ms = local_observation_timestamp - reference_timestamp

This makes stale-reference regimes measurable instead of silently treating every reference price
as equally fresh.

A large raw basis or gross edge is not automatically alpha. It can reflect stale reference data,
an underlying-market closure, fees, a wide bStock spread, temporary market impact, unavailable
borrow, or genuine price discovery.

## Discovery

The scanner does not maintain a hard-coded stock list. It selects trading USDT Spot pairs whose
Binance base asset follows the bStocks B-suffix convention, then confirms that Binance reports
referencePrice.calculationType as EXTERNAL.

This is a practical CEX discovery rule, not an authoritative corporate-action/security-master
substitute. When Binance Web3 RWA API credentials are available, its bStocks metadata should be
joined in as an additional validation source.

## Dataset

Each run appends one cross-sectional snapshot to data/basis_snapshots.csv. Raw data is ignored
by Git. When collection volume grows, migrate the append path to Parquet and query with DuckDB;
do not build a custom time-series database first.

## Next validation steps

1. Label US pre-market / regular / after-hours / closed regimes using authoritative upstream data.
2. Collect enough snapshots to estimate basis persistence and mean reversion by regime.
3. Add historical fee schedules, slippage and actual short-borrow constraints.
4. Measure post-signal forward returns at multiple horizons.
5. Validate on held-out dates before any live execution integration.
