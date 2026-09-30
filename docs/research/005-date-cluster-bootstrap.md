# Research 005 — date-clustered uncertainty

## Motivation

A one-second collector can create tens of thousands of observations in one market day. Those rows
are not tens of thousands of independent experiments: quotes, reference prices and market regime
are strongly dependent within a day.

Using raw row count as statistical sample size would therefore produce misleadingly narrow
confidence intervals.

## Daily clusters

The uncertainty layer first collapses matched observations to one mean net return per market date
for each research cell:

    sample (TRAIN / TEST / UNSPLIT)
    horizon
    market session
    edge bucket
    preferred side

The daily output also records matched trade count, symbol count, median net return, positive trade
rate and mean signal edge.

Output:

    data/research/daily_net_summary.csv

## Cluster bootstrap

For each research cell, the bootstrap resamples market dates with replacement and computes the
mean of the resampled daily means.

Default configuration:

    2000 resamples
    95% confidence interval
    minimum 5 market dates
    deterministic seed 8723

Output:

    data/research/bootstrap_ci.csv

Important fields:

    market_dates
    matched_trades
    mean_daily_net_bps
    median_daily_net_bps
    positive_day_rate
    ci_low_bps
    ci_high_bps
    ci_excludes_zero
    status

If there are fewer than five market dates, status is INSUFFICIENT_DATES and the confidence
interval is intentionally left null.

## Interpretation

A positive row-level mean is not sufficient evidence. A stronger research result has:

1. positive net returns after cost assumptions;
2. persistence in TEST dates;
3. enough independent market-date clusters;
4. a date-clustered confidence interval that is economically meaningful;
5. stability across nearby parameter choices rather than a single optimized threshold.

This bootstrap is a practical dependence-aware diagnostic, not a substitute for a full
microstructure inference model. The next stage should examine threshold stability and multiple
testing before promoting any hypothesis.
