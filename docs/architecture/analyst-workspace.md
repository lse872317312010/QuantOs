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
