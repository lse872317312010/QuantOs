# Decision synthesis

## Purpose

The decision layer converts independent evidence and risk context into a ranked slate for human
review. It does not place orders and it does not hide its logic behind an opaque model.

## Scoring

Each directional evidence item contributes:

    directional_score × evidence_confidence × domain_weight

The combined directional score is normalized to -1..1. Confidence is the weighted average evidence
confidence, reduced by:

- contradiction between positive and negative evidence;
- overall risk score.

All domain weights and thresholds live in `SynthesisConfig`.

## Risk authority

A hard risk blocker always produces:

    state = BLOCKED
    stance = AVOID
    priority_score = 0

No amount of positive strategy evidence can override a blocker.

## Candidate explanation

Each candidate carries:

- directional decision score;
- human-review priority score;
- supporting evidence summaries;
- contradicting evidence summaries;
- risk warnings / blockers as invalidation conditions;
- simple alternatives;
- full original evidence and risk objects.

The snapshot list is sorted for review priority. That order is not an execution instruction.

## Decision journal

`DecisionJournal` writes each point-in-time `DecisionSnapshot` as append-only JSONL. This keeps
the exact historical view available for later review and outcome calibration.

The journal is intentionally an analytical audit record, not an OMS or trade blotter.
