# Research 008 — explicit research promotion gates

## Motivation

A research pipeline should not rely on visually scanning CSV files and deciding after the fact which
result "looks good." Promotion criteria must be written down before deployment decisions and should
be machine-readable.

## Inputs

The gate combines:

- Research 006 TRAIN-only threshold stability and FDR screening;
- Research 007 repeated walk-forward out-of-sample evidence.

No TEST result can override a TRAIN rejection.

## Default states

`REJECTED_TRAIN`
: the candidate failed the TRAIN-only stability/FDR screen.

`INSUFFICIENT_WALK_FORWARD`
: the TRAIN candidate has no repeated walk-forward evidence yet.

`INSUFFICIENT_OOS_HISTORY`
: walk-forward evidence exists but does not meet the minimum number of selected folds or test dates.

`OOS_WEAK`
: enough OOS history exists, but average net economics or positive-fold rate misses the configured
  threshold.

`RESEARCH_CANDIDATE`
: the configured research gates are met. This state is deliberately not called "production ready."

Default numerical gates:

    selected folds >= 3
    total OOS market dates >= 10
    positive OOS fold rate >= 60%
    mean OOS daily net return > 0 bps

All thresholds are CLI-configurable and persisted into analysis_config.json.

## Output

    data/research/promotion_gate.csv

## Non-meaning of RESEARCH_CANDIDATE

This state does not authorize live capital. It only means the statistical research pipeline has
enough evidence to justify the next validation stage: execution simulation, fill/slippage stress,
capacity/liquidity checks, shadow trading and operational controls.
