# Continuous investment learning: evidence -> hypotheses -> outcomes

Status: target architecture plus first domain-contract implementation. This is not a
claim that an autonomous research service or live strategy is deployed.

## Product objective

QuantOs should help a person build calibrated investment judgment: identify a change,
explain plausible mechanisms, retrieve comparable cases AND counterexamples, register
an expectation before the outcome, and learn from what actually happens. A persuasive
explanation is not evidence of predictive skill. Stable returns are an evaluation goal,
not a promised property of the software.

The existing market/data, Evidence, RiskAssessment, DecisionSnapshot, analyst workspace
and decision journal remain the platform. bStocks is one research vertical, not the
system boundary. No broker permissions or orders are needed for this workflow.

## Reuse decisions (official sources reviewed 2026-11-24)

| Responsibility | Upstream / existing component | Scope and decision |
| --- | --- | --- |
| Numerical market history | Existing QuantOs Parquet/DuckDB data plane | Reuse; do not put tick streams in an LLM graph |
| Temporal document/entity relationships | Graphiti | Preferred integration candidate; structured/text episodes, provenance and temporal retrieval; database/LLM operating costs still exist |
| Stateful research workflow | LangGraph | Preferred integration candidate for checkpoints and human review; no home-grown scheduler or agent event bus |
| Multi-perspective financial analysis | TradingAgents | Evaluate as an optional analysis provider, not an authority or automatic capital allocator |
| Automated factor/model experiments | RD-Agent + Qlib | Offline, isolated research workers with bounded search budgets; not a drop-in bStocks market simulator |
| Execution-aware replay | Existing research pipeline; NautilusTrader when required | Never rebuild matching, order lifecycle or a generic backtest engine |
| Experiment provenance | MLflow | Log data/code/prompt/model versions, tried hypotheses, rejected runs and artifacts; metadata alone does not preserve source bytes |
| Learning review UI | Existing analyst workspace/journal | Extend its briefs/case detail before creating a second platform |

These are design selections, not installed dependencies in this change. Pin and test a
compatible release for each adapter before integration. Verify licenses, data rights,
provider availability and external processing of documents separately. Do not install
all candidates at once or maintain a private fork without demonstrated need.

Official references:
- Graphiti: https://help.getzep.com/v4/graphiti/getting-started/overview
- LangGraph: https://docs.langchain.com/oss/python/langgraph/overview
- Human review: https://docs.langchain.com/oss/python/langgraph/interrupts
- TradingAgents: https://github.com/TauricResearch/TradingAgents
- RD-Agent: https://github.com/microsoft/RD-Agent/blob/main/docs/scens/quant_agent_fin.rst
- Qlib: https://github.com/microsoft/qlib
- MLflow: https://mlflow.org/docs/latest/ml/tracking

## End-to-end flow

    official / licensed data and documents
      -> immutable source versions, provenance and quality checks
      -> time-aware entity/event links and point-in-time retrieval
      -> mechanism hypothesis + counterargument + invalidation rule
      -> frozen hypothesis / forecast registration
      -> historical exploration OR rolling OOS OR forward shadow observation
      -> mature outcome + cost/risk evaluation + uncertainty
      -> case memory and calibration
      -> analyst brief / human review

Knowledge graph edges need explicit epistemic types: a reported observation, an
interpretation, an association, or a proposed causal mechanism. Never turn LLM extraction
or correlation into proven causation. Distinguish underlying economic events, venue
prices, token mechanics, and account eligibility when a market requires it.

## Three memories

1. Source memory: original document/version/hash, publication and first-seen times,
   source attribution, affected instruments and revisions. Syndicated stories retain the
   same origin identifier; ten copies are not ten independent confirmations.
2. Hypothesis memory: mechanism, expected direction/horizon, signal definition, benchmark,
   counterarguments, falsification rule and immutable versions. Include rejected ideas.
3. Case memory: the prediction made at the time, alternatives, subsequent evidence,
   matured outcomes, costs, regime and error explanation. Retrieve failures as well as wins.

An LLM may propose and summarize. It must not fabricate missing numbers, self-grade an
experiment, execute instructions embedded in a news article, or silently rewrite a past
prediction. Deterministic code/library outputs remain the source for numerical results.

## Time and availability

Persist UTC; present reviews in the user's configured timezone (Asia/Shanghai for this
workflow). Publication time, first seen time, extraction/registration time, event time and
label availability are different. A filing describing last quarter was not known last
quarter. A revised release is a new version, not a replacement for historical knowledge.

For live/paper knowledge, this change uses the conservative rule:

    available_at = max(published_at, first_seen_at, recorded_at)
    every hypothesis citation.available_at <= hypothesis.registered_at

Historical exploration can use a separately documented publication-time policy only
when historical source vintages and realistic access delays are preserved. It cannot
masquerade as a prospectively observed forecast. Retrieval filters alone do not establish
that a present-day LLM lacks knowledge of subsequent historical outcomes. Model/prompt
versions and contamination limitations must be disclosed; prospective shadow evaluation
is a separate, stronger test.

A forecast for a five-day horizon is PENDING until that horizon closes and the final
label becomes available. Intraday price changes may update monitoring, not finalize a
five-day success label. Trading-day horizons must be resolved by the existing calendar
adapter before creating an explicit target timestamp; this contract uses elapsed seconds.

## What 'real-time backtesting' means here

| Lane | Trigger | Output | Constraint |
| --- | --- | --- | --- |
| Monitoring | New valid data / event | Updated exposure, features, evidence and quality | Deterministic updates need not call an LLM |
| Historical exploration | New hypothesis version or material data revision | Cached replay / event study from a mature engine | Exploratory, not fresh out-of-sample evidence |
| Rolling OOS validation | Scheduled eligible window | Frozen-version results on later data | Purge training labels whose realized endpoints enter validation; embargo where needed |
| Forward shadow evaluation | Previously registered forecast matures | Observed result with costs and calibration | No orders; no hindsight parameter changes |
| Promotion review | Predefined evidence gates pass | Human-review candidate or rejection | No automatic live deployment |

Do not run a full history or retrain a model on every price update. Debounce duplicate
stories; invalidate only impacted features/hypotheses; cache by source/data/code/parameter
versions. Freeze a model used for prospective forecasts. Adaptive candidates belong to
separate experiments. Impose LLM-token, experiment-count and compute budgets.

## Validation and intuition

Each experiment must specify its universe as of the decision date, return definition,
benchmark, realistic decision-to-entry delay, fees/slippage, exit rules, and risk limits.
A reference price is not a guaranteed executable exit. Distinguish event-study returns
from a portfolio backtest with cash, overlapping positions and drawdown.

Compare with no-change/no-skill and simple investment baselines. Report coverage and
missing labels, effect size, uncertainty, clustered/overlapping observations, turnover,
concentration, tail behavior and sensitivity across regimes. Track all tested hypotheses;
repeatedly inspecting a holdout makes it a development set. Use mature statistics/CV
libraries rather than writing a new inference engine.

Use an upstream proper-scoring implementation (for example Brier score for a well-defined
binary event) and reliability diagrams to assess registered probabilities, not an LLM's
self-reported confidence. Strategy selection should require OOS and prospective evidence,
realistic costs and robustness, not only a good historical Sharpe ratio.

For the human, each case should answer:

    What changed? What did we know then? Why might it matter?
    What else could explain it? What would falsify our view?
    What happened in comparable cases, including failures?
    What did we predict before the result? What actually happened?
    What should change in our belief, and what remains unknown?

## Implementation boundaries and next acceptance gates

Implemented in this change:
- EvidenceLink provenance and availability checks, referring to existing Evidence IDs;
- immutable HypothesisSpec with benchmark, counterarguments and falsification;
- ForecastRegistration, OutcomeObservation and mature-label scoring eligibility;
- isolated regression tests for chronology, duplication, immutability and invalid inputs.

Not implemented by this change:
- authenticated data feeds, a news crawler, Graphiti persistence or LangGraph execution;
- LLM-generated hypotheses, source verification, real-time workers or a new dashboard;
- actual probability scoring, automatic backtesting, strategy promotion or order submission.

Next vertical slice, in order:
1. One authorized document source + existing market data. Preserve source bytes/vintages;
   register links in the existing data/evidence plane. Manually check extracted facts.
2. One Graphiti adapter, bounded retrieval, contradiction visibility and as-of contract tests.
3. One LangGraph workflow: retrieve -> hypothesize -> challenge -> human review -> register;
   use an existing durable checkpoint and journal, no second store of truth.
4. One supported mature replay engine + MLflow run linkage. Record full hypotheses, code,
   data snapshots and cost assumptions. Do not claim historical knowledge is prospective.
5. Resolve one pre-registered forecast after maturity and render its learning case through
   the existing analyst workspace. Calibrate only after enough genuinely distinct cases.

A green unit test proves a contract, not financial efficacy. A complete slice must also
pass integration/failure tests, access checks and a real end-to-end observation. No daemon
or cloud service is started merely by merging this document.
