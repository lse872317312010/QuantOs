# Analyst review workspace

## Goal

The first workspace layer validates the daily analytical workflow before a web UI is chosen.

A review session runs:

    watchlist
      -> evidence providers
      -> risk providers
      -> decision synthesis
      -> ranked decision slate
      -> journal
      -> human-readable brief

## Why this comes before a dashboard

The platform should stabilize the review workflow and contracts before choosing presentation
technology. A dashboard can later consume the same ReviewSession / DecisionSnapshot objects.

## Failure behavior

Evidence and risk provider failures are preserved in the session. One provider failure does not
erase the rest of the review. The final brief exposes those failures explicitly so missing analysis
cannot silently look like neutral evidence.

The optional `required_providers` argument to `EvidenceEngine` names the evidence sources
needed for a particular review. A required source that fails, returns nothing or supplies
evidence available after the cutoff blocks its instrument. An optional source failure appears
in the brief and valid evidence from other sources remains usable. Each provider contributes
its batch only after every item passes the cutoff. Configured risk checks are mandatory.

The decision journal records UTC review and evidence times. An evidence producer can provide
`available_at` for delayed receipt or revision. For a directly observed input, the default is
`observed_at`. Snapshot-backed evidence retains its source observation time. An event announced
for a future date can be evidence now when its observation and availability are known now.

Historical journals keep their original contents. A legacy candidate whose source availability
or completed risk checks cannot be established remains unverified. To compare a reconstructed
review, use the same inputs and cutoff, write to a new journal, and retain both versions.

### Strict JSON journal output

New rows are serialized with the standard-library JSON encoder's `allow_nan=False`.
Non-finite floating-point values are represented as JSON null **with** an explicit
top-level `nonfinite_values` list. Each entry has a `path` array of string object
keys and integer array indices relative to the row root, and a `kind` of `NaN`,
`Infinity` or `-Infinity`. The sidecar is absent when no such value was encountered.
A null at a listed path is an invalid numeric observation, not a valid zero or
an ordinary missing value; unlisted nulls and literal strings are not markers.
A duplicate key after string conversion is rejected before appending because it
would make audit paths ambiguous. Decisions and risk assessments are not recomputed
by serialization.

`DecisionJournal.entries()` retains its legacy permissive reader for compatibility;
old rows may contain nonstandard tokens and are not silently normalized or revalidated.
Consumers requiring strict JSON must validate individual historical rows and isolate
invalid or unverifiable records before using them as research or scoring evidence.
Never rewrite the old file to make it appear valid; a reconstruction belongs in a
separate journal. New valid rows can still be appended to an older file.

## Output

The Markdown renderer contains:

- market context;
- ranked candidates;
- confidence and scores;
- supporting and contradicting evidence;
- risk warnings / blockers;
- invalidation conditions;
- alternatives;
- alerts;
- provider failures.

The report explicitly states that ranking is for human review and is not an execution instruction.
