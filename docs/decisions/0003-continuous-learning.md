# ADR-0003: Evidence-grounded continuous learning, not autonomous trading

Status: proposed for integration; domain contracts implemented in this change.

## Context

The user prioritizes learning investment relationships and building long-lived, testable
strategies over selecting a narrow strategy or automating an account. QuantOs already has
point-in-time market data, evidence/risk providers, decision synthesis and an analyst
workspace. Those are reused, not replaced by a new platform.

## Decision

- Make source -> hypothesis -> preregistered expectation -> mature outcome -> case review
  the primary product loop. A market adapter is not the platform boundary.
- Preserve observations, interpretations and proposed causal mechanisms as distinct types.
  Confidence must come from evidence and calibrated outcomes, not agent agreement.
- Prefer Graphiti for temporal knowledge, LangGraph for stateful workflow and human review,
  MLflow for experiment tracking. Evaluate TradingAgents as an optional analysis provider
  and RD-Agent/Qlib as isolated research workers. See the cited upstream comparison in
  ../architecture/continuous-learning.md. Integrate one component at a time.
- Reuse existing analytics and mature backtest engines. Do not implement a graph database,
  crawler framework, agent runtime, generic backtester, scheduler or execution system.
- Keep backtests, rolling out-of-sample tests and prospective shadow outcomes separate.
  No immature label, revised historical document or late-extracted explanation is counted
  as a fact known by the original live forecast. LLM historical contamination is an explicit
  limitation, not solved by a timestamp field alone.
- Record forecast IDs, hypothesis versions, data/code/model/prompt versions and outcomes in
  existing durable artifacts/journals. Dataclass immutability is NOT a durable audit ledger;
  the integration must enforce append-only versions and unique registration IDs.
- No trading permissions, API secrets, paid services or background processes are enabled
  by this change. User review remains mandatory before any future action handoff.

## Consequences

The first patch adds domain contracts and chronology tests without new runtime dependencies.
It does not claim that a complete knowledge learner or live backtester exists. Subsequent
adapters must demonstrate source availability correctness and evidence traceability before
adding more agents or increasing the experiment budget. The success measure is better
calibrated, reproducible judgment, not more frequent trading or more confident prose.
