# Research 007 — walk-forward out-of-sample validation

## Motivation

A single chronological holdout can still be lucky or regime-specific. The validation process should
be repeated through time so each test window is strictly later than the training information used
to select a candidate.

## Upstream

QuantOs delegates the generic splitter to `skfolio.model_selection.WalkForward`. The repository
does not implement its own generic time-series cross-validator.

## Fold procedure

For every fold:

1. use whole New York market dates as the atomic observations;
2. build chronological train/test windows with an optional purge gap;
3. rerun Research 006 threshold screening using only the fold's TRAIN dates;
4. freeze the resulting TRAIN selection flags;
5. report performance on the immediately later TEST dates;
6. never use a TEST result to change the fold's candidate selection.

Default configuration:

    train dates: 20
    test dates: 5
    purge dates: 1
    expanding train window: yes

The purge date separates training from testing and reduces boundary leakage from labels or state
that can overlap adjacent dates.

## Outputs

    data/research/walk_forward_folds.csv
    data/research/walk_forward_summary.csv

The fold file contains the complete selection and OOS result for every threshold. The summary only
aggregates rows whose `stable_train_candidate` flag was true before the corresponding test window
was observed.

## Interpretation

A stronger candidate should be repeatedly selected in training windows and retain positive
cost-adjusted OOS economics across multiple later folds. One positive fold is not sufficient.

This remains research validation. Event-driven execution simulation, fill uncertainty, capacity,
operational risk and live shadow trading remain separate gates.
