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

- missing quality evidence generates a warning;
- degraded evidence raises risk;
- critically unusable/unavailable source evidence creates a blocker.

### LiquidityRiskProvider

Consumes LIQUIDITY evidence and evaluates top-of-book spread.

The default thresholds are configurable. Wide spreads can produce warnings or hard blockers.

### ConcentrationRiskProvider

Uses portfolio context to measure the existing absolute portfolio weight of the instrument.

The current provider is intentionally simple. Correlation, sector/theme crowding and look-through
exposures are later extensions.

## Aggregation

`RiskEngine` runs independent RiskProvider implementations and combines them conservatively:

- overall risk = maximum provider risk score;
- each named dimension keeps its maximum score;
- blockers are unioned;
- warnings are unioned;
- one provider failure does not discard valid risk results from other providers.

This design avoids the dangerous behavior where a low-risk dimension averages away a critical
blocker.

## Decision boundary

A later decision synthesizer must never emit a normal CANDIDATE state when RiskAssessment contains
hard blockers. That invariant is already enforced by the core DecisionCandidate contract.
