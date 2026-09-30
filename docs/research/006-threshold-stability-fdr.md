# Research 006 — threshold stability and multiple-testing control

## Why this exists

A threshold discovered by sweeping many edge cutoffs can look attractive purely by chance. TEST
data must not be used to choose that threshold, and nominal p-values must not be read as if only
one hypothesis was tested.

## Method

The report sweeps configured executable-edge thresholds over already cost-adjusted outcomes. For
each threshold, horizon, US-equity session and preferred side it:

1. collapses observations to one mean net return per market date;
2. computes a one-sided one-sample test on TRAIN daily means using SciPy;
3. applies SciPy's Benjamini-Hochberg false-discovery-rate correction across TRAIN candidates;
4. marks a candidate as stable only when it passes TRAIN FDR and at least one adjacent threshold
   also passes;
5. reports TEST metrics only after the TRAIN-only selection fields have been computed.

The implementation deliberately delegates statistical primitives to SciPy rather than reimplementing
generic hypothesis testing or FDR procedures.

## Output

    data/research/threshold_stability.csv

Key fields:

    threshold_bps
    train_market_dates
    train_mean_daily_net_bps
    train_p_value
    train_fdr_q_value
    train_fdr_pass
    adjacent_train_passes
    stable_train_candidate
    test_market_dates
    test_mean_daily_net_bps

A TEST result never changes `train_fdr_pass` or `stable_train_candidate`.

## Interpretation

This is a screening layer, not proof of deployable alpha. A candidate still needs enough independent
dates, economically material net returns, persistence in untouched TEST dates, liquidity/capacity
checks, and eventually event-driven execution validation before any live-capital decision.
