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

The purge gap excludes signal dates. Both holdout and walk-forward also check the timestamp of
the quote used to settle each label (`label_end_timestamp_ms`). A TRAIN exit must precede
midnight in New York at the start of the first TEST date. A TEST exit must precede midnight
after its last date. Equality crosses the boundary. A quote can arrive after the intended horizon,
and a New York date can have 23 or 25 hours.

The outcome Parquet keeps crossing rows as `PURGED`. Unmatched signals retain their sample
and null return for coverage. The pooled forward summary describes all matches. Threshold
screening and daily bootstrap inputs exclude purged rows. Each rolling fold recalculates
eligibility and reports `purged_label_rows`. The holdout count is in `analysis_config.json`.

## Outputs

    data/research/walk_forward_folds.csv
    data/research/walk_forward_summary.csv

The fold file contains the complete selection and OOS result for every threshold. The summary only
aggregates rows whose `stable_train_candidate` flag was true before the corresponding test window
was observed.

### Replaying earlier runs

Retain the original files for audit. Re-run `bstocks-analyze` on the original observations with
the same options and a fresh `--output-dir` before using any earlier holdout, bootstrap, threshold,
walk-forward or promotion output for review. Older outcome Parquet files carrying the matched
`_future_timestamp_ms` can also be repartitioned directly. A labeled return with an unknown
endpoint cannot enter the split. Promotion CSVs from the updated pipeline carry
`label_window_policy` and their UTC availability time. The evidence provider rejects unversioned
gates and exposes a regenerated gate only from its availability time onward.

## Interpretation

A stronger candidate should be repeatedly selected in training windows and retain positive
cost-adjusted OOS economics across multiple later folds. One positive fold is not sufficient.

This remains research validation. Event-driven execution simulation, fill uncertainty, capacity,
operational risk and live shadow trading remain separate gates.
