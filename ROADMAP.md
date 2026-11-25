# QuantOs roadmap

本路线图依据 [CONSTITUTION.md](CONSTITUTION.md) v1.0.0（2026-11-24）编制。它规定交付顺序和验收证据，不授予资金、数据、服务或费用权限。长期原则变更走 C15 修宪；具体实现及框架替换走受审查 ADR。开发与验收遵循 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [AGENTS.md](AGENTS.md)。

**状态基线：2026-11-25。** 默认分支截至本次核对为 `cc1e40b9cdc5a8ba238b8800c77ec59c68293ed6`（PR #15）。宪法仍在 [PR #17](https://github.com/lse872317312010/QuantOs/pull/17) 等待所有者明确批准并人工合并；本路线图是与该提案配套的实施计划，不宣称宪法已经生效。[PR #16](https://github.com/lse872317312010/QuantOs/pull/16) 学习协议仍未合并，其当前提交 `dd735b384ab61edef5f9a7d67042614a7450d624` 已报告 CI 成功，但 UTC/DST 实质审查问题仍未解决。

## 1. 北极星：改善人的投资认知

    获准资料与行情 → 来源及版本 → 时间点证据与关系
    → 可证伪假设 → 事前登记的预测 → 分离的历史/OOS/前向验证
    → 成熟结果 → 案例记忆与校准 → 人工复盘 → 新版本假设

首个最小闭环：一类获准资料 + 一组现有行情 + 一种明确结果事件，形成有反证、有基准的假设卡；执行一次可复现历史检验；登记一条真实前向预测；在结果成熟且可用后完成一条复盘案例。不得用合成样本或历史回填替代真实前向观察。

交付价值分别衡量：

| 维度 | 验收依据 |
| --- | --- |
| 工程可靠性 | 时间、溯源、事务、失败降级、重启恢复的行为与集成测试 |
| 判断质量 | 预登记预测的覆盖率、成熟样本、基准比较、适当概率评分与可靠性；保留反例和未知 |
| 投资有效性 | 独立样本外及前向证据、现实成本和约束、风险与适用环境；事件研究不等于账户收益 |
| 个人可维护性 | 北京时间审阅节奏、实际资源/费用记录、可恢复运行、无需持续盯盘 |

前三项不能相互替代；一条成熟案例仅证明流程接通。允许证据不足、暂不行动、撤回判断和无法归因。核心不接真实资金账户也必须有价值。

## 2. 当前关键路径：P0 → P1 → P2 → P3 → P4 → P5 → P6

P0–P6 是验收门槛而不是工期承诺。全部未验收。可并行开展不污染数据或扩大权限的准备工作，但不能绕过前一关键门槛采用结果、部署后续闭环或用市场/框架数量冒充完成。历史 A–G 清单只是可复用资产。

| 门槛 | 对应条款 | 前置 | 当前状态 |
| --- | --- | --- | --- |
| P0 正确性与治理基线 | C00, C05, C08–C10, C12, C14–C15 | 所有者采纳治理规范；可先独立修复缺陷 | 阻断：#16 时间审查 |
| P1 来源与证据记忆 | C03–C07, C12 | P0 | 未验收 |
| P2 时序知识与反证检索 | C03–C07, C11–C13 | P1 | 未验收 |
| P3 假设与事前登记 | C02, C05–C09, C12–C13 | P2 | 未验收 |
| P4 实验与持续验证 | C03, C05, C08–C10, C12–C14 | P3 | 未验收 |
| P5 成熟结果与案例闭环 | C01, C06–C11, C13–C14 | P4 | 未验收 |
| P6 受控运行与扩展 | C01–C04, C11–C15 | P5 | 未验收 |

### P0 — 正确性与治理基线（下一开发任务）

- [ ] 在 #16 或明确关联的修复 PR 中处理 [UTC/DST 审查意见](https://github.com/lse872317312010/QuantOs/pull/16#discussion_r4675831648)：真实时刻比较、排序、期限计算统一 UTC；覆盖春季跳变、秋季重复时刻（fold）、跨日、边界相等、晚到/修订、未来证据拒绝及提前评分。
- [ ] 检查现有 data/evidence/risk/decision/workspace/journal 的时间及可用性语义；交易日期限复用成熟日历，明确事件时间不等于信息可用时间；列出受影响历史产物并隔离或重算。
- [ ] 审计旧研究标签实际结束点、分割泄漏与 purge；审计缺失风险评估/关键 provider 失败是否仍能晋级、未来 evidence 是否被决策层接受。未经验证的路径不得用于正式结论；为实质缺口建立阻断测试及修复记录。
- [ ] 记录治理采纳、适用检查、未解决审查与服务端保护状态。分支保护/ruleset 由有权限维护者另行核验配置，不能从 PR 模板推断已启用。

**退出证据：** 目标提交的相关回归测试、全套适用 CI、审查关闭或人工确认的不适用记录；明确历史结果影响。P0 未通过不得将 #16 或受影响旧结果作为正式预测/评分依据。

### P1 — 来源与证据记忆

- [ ] 选择一类实际获准文档来源（具体提供方待权限及许可评估）和已有行情，记录访问、保存、外部处理许可及费用；不要求真实账户。
- [ ] 复用 data/evidence 与 Parquet/DuckDB，区分原文及版本、内容定位、稳定 evidence ID、来源家族、发布/接收/记录/可用时刻和提取版本；引用可返回原文位置。
- [ ] 将观察、解释、统计关联和因果假设分开；保留支持、反对、背景、修订和共同原始来源；不得以转载数量提升独立证据数。
- [ ] 将数据源连接健康、接收序列、报价新鲜度、缺失和失败纳入保守降级；关键源缺失应阻断相关判断。

**退出证据：** 一份真实获准原文和对应行情的完整溯源样例；人工抽查事实与原文一致；修订、晚到、重复转载、断流与静止报价区分的集成测试。不得仅有哈希或合成 fixture。

### P2 — 时序知识与反证检索

- [ ] 评估一个成熟时序知识上游（候选 Graphiti）和一个必要后端；先验证版本、许可、费用、时间语义及可重建性，必要时 ADR。
- [ ] 构建薄适配层：实体、事件、关系、有效时间与可用时间，支持按 as-of 检索与来源归属；图谱仅为可重建投影，原文/预测仍保留在权威记录。
- [ ] 检索反例、失败案例、替代解释及相反证据；外部文本不得作为工具或权限指令。限制检索、模型调用与重复处理。

**退出证据：** 基于 P1 真实资料的时间点检索样例；晚录事实、历史修订、冲突及来源回链测试；从原始记录重建投影的演示。LLM 后见知识限制仍须披露。

### P3 — 可证伪假设与持久化事前登记

- [ ] 在 #16 通过 P0 后复用学习协议，补足假设/预测/输入/模型/提示版本、基准、事件定义、概率或预期量、期限、反证、人工审核及撤回关联。
- [ ] 在现有存储/日志体系内确立唯一权威登记，使用成熟事务存储实现唯一约束、幂等重试、追加版本与恢复；不把 frozen dataclass 或 JSONL 自动视作耐久登记。
- [ ] 使用现有 workspace 完成检索→提出假设→反证→人工审阅→登记；先跑最小可执行流程，再按必要缺口评估 LangGraph 等成熟编排。
- [ ] 风险阻断和关键输入缺失不能被合成置信度覆盖；记录规则版本，明确现有 decision_score/priority_score 是启发式审阅指标而非预测概率。

**退出证据：** 一张有原文引用、基准、反证及审核记录的真实假设卡；唯一登记、并发/重试、冲突、追加版本、崩溃恢复、撤回及未来证据拒绝测试；原预测可查且不可静默改写。

### P4 — 可复现实验与连续验证

- [ ] 复用现有 bStocks 研究与成熟回放/统计工具；按实际缺口评估 MLflow、成熟回放引擎，不重造回测、撮合或实验平台。
- [ ] 将研究规格、全部尝试、数据快照、代码/参数/模型/提示版本、成本、基准、交易池和结果记录关联到假设/预测。
- [ ] 明确区分监测、历史探索、滚动 OOS、前向影子验证；实际标签结束点不得跨验证边界，反复使用的 holdout 重新归类研发数据。
- [ ] 记录决策到成交延迟、费用、滑点、流动性、退出、风险、缺失标签、覆盖率、效应量、不确定性、依赖样本、尾部与环境；不可成交参考价及无法借入的做空只作理论研究。若评价组合策略，必须另计资金占用与重叠仓位。
- [ ] 冻结正式前向预测的规则与模型，适应性候选另开实验；公开 LLM 历史污染局限。

**退出证据：** 一次真实输入驱动的可复现实验及其版本化产物；简单基准、失败结果、成本与 OOS 边界报告；重跑一致性及实际标签跨界拒绝测试。通过只意味着可进入前向学习，不意味着策略已有效。

### P5 — 成熟结果、案例记忆与人工复盘

- [ ] 对真实事前登记预测，在窗口结束且结果可用后关联版本化标签；区分未到期、缺失、尚不可用、已成熟、撤回/修订，不回填成功。
- [ ] 通过现有 analyst workspace/journal 展示来源、原预测、替代解释、后续证据、结果、反例及未知；保存成功和失败案例，检索不能只选赢家。
- [ ] 在足够且有代表性的成熟样本后，使用成熟概率评分（如适用的 Brier score）与可靠性分析，比较简单基准并报告样本依赖、覆盖率及不确定性；未达样本要求明确“证据不足”。
- [ ] 保持证据可靠性、预测概率、策略有效性分离；人工复盘产生新假设版本，不修改原登记。

**退出证据：** 至少一个有真实事前时间记录、成熟标签及可重放引用的完整前向案例；未成熟/缺失不得评分的测试；复盘简报及人工核查。长期校准和投资有效性另需更多独立样本，不随此门槛自动通过。

### P6 — 受控运行与扩展

- [ ] 先明确部署配置、责任人、启停、运行预算、异常恢复、缓存/增量更新及数据健康；获得实际授权后验证持续运行，不默认开启服务或付费任务。
- [ ] 默认 Asia/Shanghai 审阅窗口与可配置摘要，重要变化触发研究，避免逐 tick 调用 LLM 或全量重算；对调用量、实验量、计算和费用设显式限制。
- [ ] 以已验证闭环为基础，再扩展第二资料/市场、跨资产风险、交互式 API/dashboard、研究探索与历史浏览；按人类决策价值和可测收益排序。
- [ ] 可选研究代理（TradingAgents、RD-Agent/Qlib 等）仅作为经评估的隔离提供方；不重建核心，不自动训练或推广未验证模型。
- [ ] 动作适配器不属于本轮交付，任何资金操作需独立批准及真实权限隔离。

**退出证据：** 经授权的真实运行记录、健康与失败恢复演示、成本/人工负担记录、相对简单基准的改进证据；第二市场用现有核心接口接入。无授权则保留离线运行，不标记已部署。

## 3. 复用与技术选型顺序

| 能力 | 已有资产/候选上游 | 接入条件 |
| --- | --- | --- |
| 行情与存储 | Binance SDK、Parquet、DuckDB、现有 data | 保持权威数据与真实可用时间 |
| 证据与风险 | evidence/risk/portfolio | 修复失败降级和时间点缺口，来源去重 |
| 时序知识 | Graphiti（候选） | P1 后、实际评估且可重建 |
| 假设与登记 | #16 学习协议、现有 journal、成熟事务存储 | P0 与 P3 验收，明确唯一权威记录 |
| 编排 | workspace；LangGraph（候选） | 最小流程先接通，再按缺口引入 |
| 验证与追踪 | 现有 bStocks、SciPy/skfolio；MLflow/成熟回放（候选） | P4 前冻结规格并评估兼容性 |
| 自动研究 | TradingAgents、RD-Agent/Qlib（候选） | P6 后置、隔离评估 |

候选不是已安装或已验证的技术承诺。新增通用能力先查上游；记录实际版本、许可证、适用边界、成本、迁移/退出方案，按 C03 处理 ADR。不得因技术选型延误最小闭环。

## 4. 验收记录与近期工作队列

每项完成记录至少包含：对应条款、PR/commit、实际检查及结果、输入/产物版本、未解决问题、权限/费用影响、回滚、部署状态和人工验收依据。状态按设计、已实现、单测通过、集成验证、部署运行、前向观察、投资有效性分别记录，不以 CI 代替投资证据。

| 顺序 | 任务 | 依赖/证据 | 状态 |
| --- | --- | --- | --- |
| 1 | 所有者审核并人工采纳宪法 | #17；C15 | 待批准 |
| 2 | 修复 #16 UTC/DST 与复查时间语义 | #16 实质审查；P0 | 阻断 |
| 3 | 审计既有研究、风险和快照关键正确性 | P0；#11–#15 既有实现 | 待核验 |
| 4 | 接入首个获准资料并建立来源版本记录 | P0；P1 | 未验收 |
| 5 | 知识检索、假设登记及持久化 | P1→P2→P3 | 未验收 |
| 6 | 可复现实验及真实预测到期复盘 | P4→P5 | 未验收 |
| 7 | 低负担运行与多市场/界面扩展 | P6；明确授权 | 未验收 |

本次路线图不修改业务代码，不安装候选框架，不启动服务，不配置账户权限或 GitHub 保护；#16 的已报告 CI 成功不消除审查阻断。后续按实际验收更新清单，不预先打勾。

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
