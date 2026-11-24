# QuantOs roadmap

本路线图受 [CONSTITUTION.md](CONSTITUTION.md) 约束，描述实施顺序而非自动授权。长期原则修改走修宪；框架替换和实现细节走 ADR；阶段完成必须提供验收证据。开发流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 当前实施顺序：先完成一个持续学习闭环

以下 P0–P6 是当前交付顺序，全部保持未验收，不能由后文历史能力清单的勾选推断已完成。2026-11-24 核对时，[PR #16](https://github.com/lse872317312010/QuantOs/pull/16) 仍是未合并的学习协议提案；其类型定义不等于服务部署。

| 门槛 | 交付范围 | 必须提供的验收证据 | 状态 |
| --- | --- | --- | --- |
| P0 正确性 | UTC 归一化、夏令时与晚到数据、预测期限与成熟标签；处理 PR #16 时间审查问题 | 跨 DST 跳变/重复时刻、跨日、未来证据和提前评分的回归测试；审查问题处理记录 | 未验收 |
| P1 一类获准资料 | 原始版本、来源归属、内容位置/哈希、实体映射，与一组现有行情关联 | 原文抽查、修订不覆盖历史、转载不重复提升可信度；访问/处理许可记录 | 未验收 |
| P2 时序知识记忆 | 一个图适配器、一个后端、时间点检索与反证展示 | 历史查询不会看见后来资料；支持与反对证据可回到原文；图可重建 | 未验收 |
| P3 研究与登记 | 检索→假设→反证→人工审核→事前登记，复用日志和成熟编排 | 重启/重试不重复登记；唯一性、事务与追加版本；缺失关键定义拒绝登记 | 未验收 |
| P4 可复现验证 | 已有研究/成熟回放引擎与实验追踪连接，成本、基准、延迟、样本外边界 | 数据/代码/模型/参数版本可复现；标签不跨验证边界；缺失结果单独报告 | 未验收 |
| P5 前向学习案例 | 到期解析、结果关联、成功/失败案例与现有工作台集成 | 真实事前预测的成熟结果；未到期不得评分；失败、缺失与无法归因可见 | 未验收 |
| P6 受控扩展 | 第二类资料/市场、交互界面、可选自动研究 | 相对简单基准的可测改进、运行成本与风险；不以数量代替质量 | 未验收 |

首个最小版本：一类资料 + 一组行情 + 一种事件 → 有反证的假设卡 → 一次历史检验 → 一条事前预测 → 一条到期复盘案例。完成一个真实案例只证明流程接通，不证明长期预测或投资能力。

候选上游接入顺序：复用现有 Parquet/DuckDB/workspace/journal；按缺口评估 Graphiti、LangGraph、MLflow 和成熟回放引擎；TradingAgents、RD-Agent/Qlib 后置。以上为可替换候选，不是已安装依赖或不可变框架承诺。每项接入先验证版本、许可、兼容性、费用和权限，再通过 ADR/PR 记录。

## 既有平台能力清单（不是当前实施顺序）

以下保留原有 A–G 架构与实现记录。`[x]` 表示此前登记的实现范围，不表示持续学习闭环、生产服务或投资有效性已经验收。P0–P6 的结果另行以实际证据更新。

## North-star workflow

A user should be able to open QuantOs and answer:

1. What is happening in the markets I care about?
2. What changed materially since my last review?
3. Which instruments or themes deserve attention?
4. What evidence supports or contradicts each idea?
5. What are the relevant risks and invalidation conditions?
6. How does the idea interact with my existing portfolio?
7. What should I watch next?

The platform should make these answers reproducible and auditable.

## Phase A — platform foundation — existing implementation

Deliver:
- canonical decision/evidence/risk contracts;
- source/market/research/risk/decision module boundaries;
- data provenance conventions;
- instrument and venue identity model;
- decision snapshot format;
- architecture and contribution rules.

Exit criterion:
new markets and evidence providers can plug in without changing the core contracts.

## Phase B — analytical data plane — capability inventory

Deliver:
- [x] canonical market-event schemas;
- [x] local Parquet + DuckDB catalog;
- [x] source registry;
- [x] freshness/completeness metrics;
- [x] point-in-time historical query API;
- [x] unified instrument registry;
- [x] multi-source as-of snapshot assembly;
- [x] adapter that registers current bStocks book/reference datasets into the generic catalog;
- [x] catalog-level source health command / report;
- [ ] second market/provider vertical beyond the current Binance bStocks domain.

Exit criterion:
the platform can answer point-in-time analytical queries across at least two data sources.

## Phase C — evidence plane — capability inventory

Deliver:
- [x] adapt current bStocks basis and research-gate outputs into generic Evidence objects;
- [x] market regime provider;
- [x] liquidity provider;
- [x] anomaly provider;
- [x] strategy/research provider interface;
- [x] provider isolation so one failed evidence source does not erase the full view;
- [ ] evidence provenance identifiers and persistence;
- [ ] confidence calibration against realized outcomes.

Exit criterion:
one instrument can have several independent evidence domains displayed together.

## Phase D — risk and portfolio context — capability inventory

Deliver:
- [x] position/exposure model;
- [x] concentration risk provider;
- [x] data-quality hard blockers;
- [x] liquidity warning/blocker provider;
- [x] conservative multi-provider risk aggregation;
- [ ] correlation/crowding views;
- [ ] event-risk provider;
- [ ] scenario/stress framework;
- [ ] portfolio-aware candidate annotations.

Exit criterion:
a strong strategy signal can be downgraded or blocked for explicit portfolio/risk reasons.

## Phase E — decision synthesis — capability inventory

Deliver:
- [x] candidate aggregation and ranking;
- [x] supporting vs contradicting evidence;
- [x] confidence and uncertainty display;
- [x] risk-veto behavior;
- [x] invalidation conditions;
- [x] alternatives;
- [x] decision snapshots and append-only journal;
- [ ] realized-outcome linkage for decision calibration;
- [ ] user-configurable synthesis profiles.

Exit criterion:
the system can produce a ranked, explainable decision slate without placing an order.

## Phase F — analyst workspace — capability inventory

Deliver:
- [x] multi-instrument analyst review session orchestration;
- [x] provider-failure visibility;
- [x] ranked human-review decision slate;
- [x] Markdown analyst brief;
- [x] decision journal integration;
- [ ] dashboard / API;
- [ ] market overview;
- [ ] interactive candidate detail / evidence tree;
- [ ] risk dashboard;
- [ ] research explorer;
- [ ] alerts delivery;
- [ ] decision-history browser.

Exit criterion:
daily market review can be performed primarily inside QuantOs.

## Phase G — optional action adapters

Only after the decision workflow is useful:
- alert delivery;
- paper/shadow execution;
- order-ticket drafts;
- optional broker/exchange handoff.

Autonomous execution is explicitly outside the current priority. Research completion does not
activate financial permissions; any future action adapter must satisfy the constitution's
approval and isolation requirements.
