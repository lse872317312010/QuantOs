# Risk and portfolio context

## Purpose

The risk layer answers a different question from the evidence layer.

Evidence asks:

> What facts or model outputs support this idea?

Risk asks:

> What could make acting on this idea inappropriate, unreliable or too concentrated right now?

Risk is allowed to veto.

## Portfolio context

`PortfolioSnapshot` is a point-in-time analytical view containing total equity and positions.

It deliberately does not contain:

- order methods;
- available execution routes;
- broker session state;
- capital-allocation automation.

Its purpose is to let analysis reason about exposure and concentration.

## Risk providers

Current generic providers:

### DataQualityRiskProvider

Consumes DATA_QUALITY evidence.

- missing quality evidence blocks the candidate;
- degraded evidence raises risk;
- critically unusable/unavailable source evidence creates a blocker.

### LiquidityRiskProvider

Consumes LIQUIDITY evidence and evaluates top-of-book spread.

The default thresholds are configurable. Wide spreads can produce warnings or hard blockers.
When this check is configured, missing spread evidence blocks the candidate.

### ConcentrationRiskProvider

Uses portfolio context to measure the existing absolute portfolio weight of the instrument.
Enabling the check requires a portfolio available by the review cutoff. A market-only review
can configure quality and liquidity checks without enabling concentration analysis.

The current provider is intentionally simple. Correlation, sector/theme crowding and look-through
exposures are later extensions.

## Aggregation

`RiskEngine` runs independent RiskProvider implementations and combines them conservatively:

- overall risk = maximum provider risk score;
- each named dimension keeps its maximum score;
- blockers are unioned;
- warnings are unioned;
- every configured risk check must return an assessment. A failure blocks the affected
  instrument and names the failed provider. Completed dimensions remain visible. An empty
  provider set or missing per-instrument assessment also blocks promotion.

This design avoids the dangerous behavior where a low-risk dimension averages away a critical
blocker.

## Decision boundary

A later decision synthesizer must never emit a normal CANDIDATE state when RiskAssessment contains
hard blockers. That invariant is already enforced by the core DecisionCandidate contract.
