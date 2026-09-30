# Research 004 — costs and chronological holdout

## Why this stage exists

Gross executable returns already cross the observed entry and exit spread. They still overstate
what a strategy can earn because trading fees, unobserved slippage, financing and short-borrow
costs remain.

This stage adds explicit cost assumptions and separates market dates chronologically so results
are not evaluated only on the same dates used to inspect the signal.

## Cost model

The model is additive in basis points:

    total_cost_bps =
        2 * taker_fee_bps_per_side
        + 2 * slippage_bps_per_side
        + short_borrow_bps_per_day * horizon_seconds / 86400  # SHORT only

    net_forward_trade_return_bps =
        gross_forward_trade_return_bps - total_cost_bps

Spread is not deducted again: the gross forward return already enters at the current ask for LONG
or current bid for SHORT and exits at the future opposite side of the book.

The default taker fee assumption is 10 bps per side. This corresponds to the Binance regular-user
standard Spot taker rate of 0.100% observed on the Binance fee page on 2026-09-30. Actual fees can
be lower or different because of VIP tier, BNB fee payment, symbol promotions, jurisdiction or
future fee changes. Always override the parameter with the account's actual applicable fee before
drawing trading conclusions.

Slippage defaults to zero so it remains a visible sensitivity parameter rather than an invented
number. Short borrow also defaults to zero until actual availability and financing terms are
measured.

Example:

    bstocks-analyze \
        --input data/stream_basis.csv \
        --taker-fee-bps-per-side 10 \
        --slippage-bps-per-side 2 \
        --short-borrow-bps-per-day 5

## Chronological holdout

Rows are never randomly split. Each observation receives market_date in America/New_York. Unique
market dates are sorted and the earliest 70% are TRAIN while the latest 30% are TEST by default.

This keeps all observations from a market date on one side of the split and reduces same-day
leakage.

If fewer than two market dates are present, rows are labeled UNSPLIT instead of pretending that an
out-of-sample test exists.

Change the holdout fraction with:

    --test-fraction 0.30

## Outputs

The forward outcome Parquet now contains:

    round_trip_fee_bps
    round_trip_slippage_bps
    borrow_cost_bps
    total_cost_bps
    net_forward_trade_return_bps
    market_date
    sample

Additional outputs:

    data/research/holdout_summary.csv
    data/research/analysis_config.json

analysis_config.json records all cost assumptions and the train/test cutoff date so a result can
be reproduced.

## Interpretation

A candidate edge is not interesting merely because gross forward return is positive. The stronger
condition is:

1. mean and median net forward return remain positive after realistic cost sensitivity;
2. the result persists in TEST market dates;
3. it is not driven only by stale book/reference states;
4. the result survives across more than one market-session regime or has an economically coherent
   reason to be regime-specific.

The next stage should estimate uncertainty and stability rather than immediately promote a
positive mean to live trading.
