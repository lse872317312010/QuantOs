# Research 003 — forward executable outcomes

## Objective

The collector now produces basis observations. The next question is not whether basis exists, but
whether a measured edge predicts a realizable future outcome after crossing the spread.

This module keeps the project in research mode: no order placement, position management or
production backtest engine is introduced.

## Session labels

US-equity sessions are derived from exchange_calendars using XNYS. That upstream supplies valid
sessions, holidays and regular-session open/close times.

For each valid session we classify:

- PRE: 04:00 America/New_York until the actual session open;
- REGULAR: actual XNYS open through actual XNYS close;
- AFTER: actual close until 20:00 America/New_York;
- CLOSED: all remaining time, including weekends and exchange holidays.

Using the actual close means early-close days are handled without hard-coding 16:00.

## Forward matching

For a signal at timestamp t and horizon H, the analysis finds the first same-symbol observation
at or after t + H. The match must be no more than max_match_lag_ms after the requested target.
This prevents a 1-second outcome from silently matching a quote many minutes later across a data
gap.

Default horizons:

    1s, 5s, 30s, 300s

## Executable return convention

If the signal's preferred side is LONG:

    forward_trade_return = future_bid / entry_ask - 1

If the preferred side is SHORT:

    forward_trade_return = 1 - future_ask / entry_bid

These metrics cross both the entry and exit spread. They are still gross of fees, slippage,
financing and borrow availability.

We also record:

    forward_mid_return_bps
    basis_convergence_bps = abs(entry_basis) - abs(future_basis)
    forward_match_lag_ms

Positive basis_convergence_bps means the absolute basis moved closer to zero.

## Freshness

The pipeline uses:

    event_age_ms = max(book_age_ms, reference_receive_age_ms)

The default analysis removes observations where event_age_ms exceeds 5 seconds. Reference engine
lag is not removed by default because long lags outside regular US-equity hours may be an
important regime rather than data corruption.

## Outputs

Run:

    pip install -e '.[research]'
    bstocks-analyze --input data/stream_basis.csv

Outputs are written to data/research:

    signals.parquet
    forward_outcomes.parquet
    forward_summary.csv

The summary groups outcomes by:

    horizon
    US-equity market session
    stream freshness bucket
    gross edge bucket
    preferred side

The first statistical question is whether larger gross edge buckets retain positive executable
forward returns after entry/exit spread crossing. Fees and slippage must be added before treating
any result as alpha.
