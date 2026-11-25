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
