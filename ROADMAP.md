# QuantOs roadmap

本路线图依据 [CONSTITUTION.md](CONSTITUTION.md) v1.0.0（2026-11-24）编制。它规定交付顺序和验收证据，不授予资金、数据、服务或费用权限。长期原则变更走 C15 修宪；具体实现及框架替换走受审查 ADR。开发与验收遵循 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [AGENTS.md](AGENTS.md)。

**2026-11-26 主线核验。** 治理、行情、预测登记、研究回测和风险修复已进入主线。研究与风险批次的 12 个实现 PR 经 11 次合并进入主线。最后一项 #42 已通过人工审阅，合并提交 `c6c57a5` 通过 Ruff 和 221 项测试。P0 尚待确认仓库外历史归档的范围。[研究与风险主线记录](#p0-closeout)

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
| P0 正确性与治理基线 | C00, C05, C08–C10, C12, C14–C15 | 治理规范已采纳 | [主线合并与复验](#p0-closeout)已核对至 `c6c57a5`。工程修复全部合入，仓库外旧结果待确认或处置。 |
| P1 来源与证据记忆 | C03–C07, C12 | P0 | 未验收 |
| P2 时序知识与反证检索 | C03–C07, C11–C13 | P1 | 未验收 |
| P3 假设与事前登记 | C02, C05–C09, C12–C13 | P2 | 未验收 |
| P4 实验与持续验证 | C03, C05, C08–C10, C12–C14 | P3 | 未验收 |
| P5 成熟结果与案例闭环 | C01, C06–C11, C13–C14 | P4 | 未验收 |
| P6 受控运行与扩展 | C01–C04, C11–C15 | P5 | 未验收 |

### P0 — 正确性与治理基线（工程已验收，历史归档待确认）

- [x] 在 #16 的 `e8a7335` 复验学习协议 UTC 时序。春季跳时、秋季重复小时、跨日、等于截止时刻、晚到/修订与提前评分均有回归覆盖。32 项专项测试通过，原[审查线程已解决](https://github.com/lse872317312010/QuantOs/pull/16#discussion_r4675831648)。
- [x] 核查行情接收时刻、交易日期限、证据可用性、风险否决和决策日志。在实际主线复跑 #38 的时序及故障样例，14 项通过。
- [ ] 确认仓库外旧行情和旧研究结果的范围。已留存的受影响批次须分类隔离，有可追溯输入时在新目录重算。
- [x] 已在 #18–#21 审计旧研究标签实际结束点、分割泄漏、样本外晋级、缺失风险与未来证据，并为复现的缺口提交阻断测试。主线集成和历史结果采用另行验收。
- [x] 记录 #17 的治理采纳和主线 CI，核对默认分支保护标记与仓库规则集列表。
- [x] 核对本轮十次研究与风险工程合并的来源提交、主线文件树、适用 CI 和代码审查，含 #26 带入的 #24。
- [x] #42 两项行为已获人工同意。已在合并后的主线验证异常行情、信号分档、无有效报价时留空以及容差内选择下一条可用退出报价。

**退出证据：** 目标提交的相关回归测试、全套适用 CI、审查关闭或人工确认的不适用记录；明确历史结果影响。P0 未通过不得将 #16 或受影响旧结果作为正式预测/评分依据。

#### 2026-11-27 验证栈收束

- [#31 交易日 UTC 边界复验](https://github.com/lse872317312010/QuantOs/pull/31) 已合入验证分支 `verify/p0-integration`（合并提交 [`6807cc1`](https://github.com/lse872317312010/QuantOs/commit/6807cc1365a18d4b6bb2f3b7610951f715114693)）。精确 head CI [45586980922](https://github.com/lse872317312010/QuantOs/actions/runs/45586980922) 与 [45600197676](https://github.com/lse872317312010/QuantOs/actions/runs/45600197676) 通过，Codex 审查无发现；合并后的推送 CI [45960664541](https://github.com/lse872317312010/QuantOs/actions/runs/45960664541) 通过。该 PR 的目标是验证分支，不是 `main`。
- [#25](https://github.com/lse872317312010/QuantOs/pull/25)、[#33](https://github.com/lse872317312010/QuantOs/pull/33)、[#35](https://github.com/lse872317312010/QuantOs/pull/35)、[#38](https://github.com/lse872317312010/QuantOs/pull/38) 已关闭归档。四者均基于 #17/#42 之前的旧基线，正文分别标注 “DO NOT MERGE” 或“不直接合并”；其底层修复已分别经 #16、#18–#22、#24（随 #26）、#26–#30、#32、#34、#36–#37、#40、#42 进入主线，证据见[研究与风险主线记录](#p0-closeout)与[主线记录](#p0-mainline)。
- 归档保留提交、评论、CI 与分支；本次收束操作本身未向 `main` 合入生产代码或实验产物，记录提交时 `main` 为 [`09419f8`](https://github.com/lse872317312010/QuantOs/commit/09419f80195f3bdf53ec5001d4cf76acddde992c)。
- [#44 移植归档时序回放](https://github.com/lse872317312010/QuantOs/pull/44) 已基于当时 `main`（`33011d6`）将归档中仍独有的三组时序回放测试和两份合成夹具移入 `tests/`，未改生产代码；GitHub CI 为 `233 passed, 81 warnings`，Codex 审查无发现，合并提交 [`ef3f3f5`](https://github.com/lse872317312010/QuantOs/commit/ef3f3f534f4b13326e3ac97697a8ea61863882f8)，合并后主线 CI [45970076126](https://github.com/lse872317312010/QuantOs/actions/runs/45970076126) 同样通过 `233 passed, 81 warnings`。
- 归档分支的旧生产代码与旧基线不进入 `main`；#44 只移植测试与合成夹具，原归档仍保留。

<a id="p0-closeout"></a>

#### 2026-11-26 研究与风险主线合并

以下每行对应一次 GitHub 主线合并及其推送 CI。每次合并均保留两个父提交，已比对合并前核验的文件树与合并结果。

| 实现 | 主线提交 | Ruff 与全套 pytest |
| --- | --- | --- |
| [#18 按实际退出时刻切分样本](https://github.com/lse872317312010/QuantOs/pull/18) | [`c65d91d`](https://github.com/lse872317312010/QuantOs/commit/c65d91d69d46c4cc552477f4486a43d99e6d1050) | [136 项通过，51 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45790823320/job/139809108146) |
| [#27 按实际持仓时长计借用成本](https://github.com/lse872317312010/QuantOs/pull/27) | [`1730e96`](https://github.com/lse872317312010/QuantOs/commit/1730e96403232fbf5b8cc82fbc49f243e03a5139) | [141 项通过，52 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45791109232/job/139810064438) |
| [#29 拒绝同毫秒重复报价](https://github.com/lse872317312010/QuantOs/pull/29) | [`c591e48`](https://github.com/lse872317312010/QuantOs/commit/c591e489a98277a627e1c91a5f98b387527d150c) | [144 项通过，53 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45791291687/job/139810682211) |
| [#20 检查样本外晋级指标](https://github.com/lse872317312010/QuantOs/pull/20) | [`88de897`](https://github.com/lse872317312010/QuantOs/commit/88de897060bfbc410e354d414189b7d85a9e4c34) | [151 项通过，53 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45791433786/job/139811167139) |
| [#30 只读核查历史报价键](https://github.com/lse872317312010/QuantOs/pull/30) | [`4bdb674`](https://github.com/lse872317312010/QuantOs/commit/4bdb674aa0f03e74956b91b2e8a7724145024a29) | [161 项通过，53 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45791631745/job/139811838818) |
| [#19 阻断未来证据及缺失风险](https://github.com/lse872317312010/QuantOs/pull/19) | [`6cfd507`](https://github.com/lse872317312010/QuantOs/commit/6cfd507f11e48de09e9de1aff9fafa5e5ee395e6) | [173 项通过，53 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45791811900/job/139812445632) |
| [#26 统一未来报价状态和 UTC 新鲜度（含 #24）](https://github.com/lse872317312010/QuantOs/pull/26) | [`32f4505`](https://github.com/lse872317312010/QuantOs/commit/32f450509997d9a41672b040a217558d8081d0ac) | [181 项通过，53 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45792003903/job/139813089639) |
| [#36 无效流动性价差触发否决](https://github.com/lse872317312010/QuantOs/pull/36) | [`994f4d5`](https://github.com/lse872317312010/QuantOs/commit/994f4d5a680d4d88ab22e6f0d38a67d5075780ef) | [195 项通过，53 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45792172507/job/139813664481) |
| [#37 无效组合估值触发否决](https://github.com/lse872317312010/QuantOs/pull/37) | [`00e5dcc`](https://github.com/lse872317312010/QuantOs/commit/00e5dcc6ea8b7328465ef3b54e6c01d410933483) | [207 项通过，53 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45792369246/job/139814352728) |
| [#40 严格 JSON 决策日志](https://github.com/lse872317312010/QuantOs/pull/40) | [`6d20ccd`](https://github.com/lse872317312010/QuantOs/commit/6d20ccd655e3c0a3b0f2c1f697684bb3379451f1) | [216 项通过，53 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45792567957/job/139815032245) |
| [#42 隔离异常研究输入](https://github.com/lse872317312010/QuantOs/pull/42) | [`c6c57a5`](https://github.com/lse872317312010/QuantOs/commit/c6c57a5592965f4f7c4dafa8d03f82feb1a18e85) | [221 项通过，63 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45798738334/job/139836080109) |

[#24](https://github.com/lse872317312010/QuantOs/pull/24) 的提交已作为 [#26](https://github.com/lse872317312010/QuantOs/pull/26) 的第二个父提交进入主线。截至 #40 的主线 `6d20ccd` 与先前候选 [#38](https://github.com/lse872317312010/QuantOs/pull/38) 的 `src/` 目录逐文件相同。该版本七组工作台回放中，六组异常被拦下且优先分为零，健康对照进入候选，七份日志均可按严格 JSON 读取。#42 合并后，原版时序与故障回放在 `c6c57a5` 上再次通过 14 项。

[#42](https://github.com/lse872317312010/QuantOs/pull/42) 源提交 `a3eb7c7` 于北京时间 18:07 获得所有者同意，18:09 合入主线。[独立候选](https://github.com/lse872317312010/QuantOs/actions/runs/45792722326/job/139815528064) 和[实际主线 CI](https://github.com/lse872317312010/QuantOs/actions/runs/45798738334/job/139836080109) 均通过 221 项测试，Git 文件树一致。同一份四行合成 CSV 在旧主线 `6d20ccd` 上产生 +∞ bp，在合并后的分析器中保留第 1、4 行。入场卖价为 101，退出买价为 103，比目标晚 100 ms，毛收益为 +198.02 bp。

已核查 `c6c57a5` 的 110 个受控文件、常见产物目录、GitHub Releases 与 15 次相关 Actions 运行的附件。上述位置未发现真实旧行情或研究结果。仓库外是否留存仍待所有者确认。原 #38 验证草稿已于 2026-11-27 关闭归档，相关评论与 CI 记录仍可查阅。

<a id="p0-mainline"></a>

#### 2026-11-26 主线合并与检查记录

| 已合并变更 | 合并提交 | 合并后的主线 CI |
| --- | --- | --- |
| [#17 项目宪法 v1.0.0](https://github.com/lse872317312010/QuantOs/pull/17) | [`991f4cc`](https://github.com/lse872317312010/QuantOs/commit/991f4cc43b9a4e5f063da17aed794672998cae82) | [Ruff 通过，66 项测试通过，14 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45745628118/job/139660844640) |
| [#16 预测登记与评分时序](https://github.com/lse872317312010/QuantOs/pull/16) | [`f0aabbc`](https://github.com/lse872317312010/QuantOs/commit/f0aabbcc4bef854dcacdeefcb72ca7840d084e48) | [Ruff 通过，98 项测试通过，14 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45761962526/job/139713830262) |
| [#28 交易日收盘期限](https://github.com/lse872317312010/QuantOs/pull/28) | [`f5158cb`](https://github.com/lse872317312010/QuantOs/commit/f5158cbf16964b9d395dd1472b80e5cb7596d410) | [Ruff 通过，112 项测试通过，38 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45762400638/job/139715207368) |
| [#21 报价可用时间](https://github.com/lse872317312010/QuantOs/pull/21) | [`ef9520d`](https://github.com/lse872317312010/QuantOs/commit/ef9520d6cdb6bbb0aaf5b1e18ef4a395b363ab42) | [Ruff 通过，119 项测试通过，42 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45779495833/job/139771241185) |
| [#22 盘口与参考价成对导入](https://github.com/lse872317312010/QuantOs/pull/22) | [`64b55cf`](https://github.com/lse872317312010/QuantOs/commit/64b55cfad94ad1ae74899202e8a11be5faf8e4bb) | [Ruff 通过，123 项测试通过，42 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45779779404/job/139772137746) |
| [#32 缺字段的来源隔离](https://github.com/lse872317312010/QuantOs/pull/32) | [`c2d1942`](https://github.com/lse872317312010/QuantOs/commit/c2d19423e73e2a7efd33aadd574f5a2e67dc00ba) | [Ruff 通过，125 项测试通过，42 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45780240802/job/139773649711) |
| [#34 无效数值的来源隔离](https://github.com/lse872317312010/QuantOs/pull/34) | [`b66b122`](https://github.com/lse872317312010/QuantOs/commit/b66b122905e26cc66216c085485eb062a13870f6) | [Ruff 通过，129 项测试通过，42 条警告](https://github.com/lse872317312010/QuantOs/actions/runs/45780520227/job/139774565142) |

行情批次从 `f5158cb` 开始依次合并。每次主线 CI 通过后，再把下一项改向 `main` 并核对逐文件补丁。四次合并的两个父提交、增量补丁和文件树均已核实，最终文件树为 `33ef072224fd8142128e2b949be82f3176b248e9`。合并前的 11 个回归用例在各自修复前均复现问题。[最终演练 CI](https://github.com/lse872317312010/QuantOs/actions/runs/45766362205/job/139728105251)

在最终主线用合成 CSV 重跑行情登记和快照。事件发生后 999 ms 尚无可读报价，1000 ms 的参考价为 11，2000 ms 的修订值为 12，3000 ms 的新参考价为空，此时买一价 20 仍可读。导入失败后两份原文件的 SHA-256 均一致，重试复用同一批文件。真实历史批次仍待核验。

#### 2026-11-25 实现与复验记录

以下保留当时的分支状态与实验结果。后续主线合并以[主线记录](#p0-mainline)为准。

| 目标提交 | 已核实行为 | 验证 |
| --- | --- | --- |
| [#16 学习协议](https://github.com/lse872317312010/QuantOs/pull/16) `e8a7335` | 以实际 UTC 时刻计算期限，只在到期且结果可用时允许评分 | [CI](https://github.com/lse872317312010/QuantOs/actions/runs/45520689905) |
| [#18 标签边界](https://github.com/lse872317312010/QuantOs/pull/18) `7b25a37` | 按实际退出报价清除跨窗标签，晋级只计有实际样本外结果的选中折；核对研究表生成时刻 | [CI](https://github.com/lse872317312010/QuantOs/actions/runs/45524543405) |
| [#19 工作台](https://github.com/lse872317312010/QuantOs/pull/19) `2544bad` | 未来证据不能进入审阅；缺风险、必需源异常或缺失触发硬阻断。其他标的和有效证据仍可审阅，结果记入 JSONL | [CI](https://github.com/lse872317312010/QuantOs/actions/runs/45522676578) |
| [#20 研究晋级](https://github.com/lse872317312010/QuantOs/pull/20) `dc991a6` | 空值、非有限值及越界的必需样本外指标阻断晋级 | [CI](https://github.com/lse872317312010/QuantOs/actions/runs/45523526909) |
| [#21 行情可用时间](https://github.com/lse872317312010/QuantOs/pull/21) `84328a3` | 区分行情事件及已收到时刻，按当时可用版本回放，REST 逐标的响应后才计时，隔离无法还原的旧观测 | [CI](https://github.com/lse872317312010/QuantOs/actions/runs/45523688359) |
| [#22 成对导入](https://github.com/lse872317312010/QuantOs/pull/22) `6c1fe60` | 依赖 #21。盘口和参考价一起登记，导入失败可重试，读取中的快照和健康报告始终使用同批文件 | [CI](https://github.com/lse872317312010/QuantOs/actions/runs/45525112631) |
| [#24 行情新鲜度](https://github.com/lse872317312010/QuantOs/pull/24) `f5f1e79` | UTC 实际经过时间；未来观测返回 UNAVAILABLE，保留诊断，不抛不存在方法异常 | [CI](https://github.com/lse872317312010/QuantOs/actions/runs/45542068550)；[最新复审无发现](https://github.com/lse872317312010/QuantOs/pull/24#issuecomment-7152224657)，旧审查线程当时仍开放（后续已关闭，见下文） |

以 `cc1e40b` 为基线，在本地临时工作树依次组合 #16、#18、#19、#21、#20 的上述内容，Git tree 为 `c352c7daeff9f8ba2f4afa16ff79673ea5e95b33`。Python 3.12 的 `ruff check .`、`git diff --check` 和全量 `pytest -q` 通过，共 131 项。离线端到端验证用 2 个标的、6 行合成观测，走通 `bstocks-register-data`、`quantos-data health`、`bstocks-analyze` 和工作台日志。3 条已匹配结果中 2 条通过切分，另 1 条的实际退出恰逢测试日午夜。组合回归还覆盖了 3 次训练选中而仅 1 折有样本外结果的情形，其晋级状态为 `INSUFFICIENT_OOS_HISTORY`。截止时刻有完整数据的标的进入人工审阅，只有未来数据的标的记录为 `BLOCKED`，优先分为 0。

加入 #22 后，组合 Git tree 为 `76f5a0ad34d063725e8e8eb27e1e200608815736`。Python 3.12.14 的 Ruff、差异检查及全量 135 项测试通过。四个新增用例在 #21 基线均复现了问题，覆盖第二份文件导出失败、第二条来源登记失败，以及在读取快照或健康报告期间切换批次。合成 CSV 经命令行重复导入后，新快照读取同批的盘口与参考价，旧文件仍可按原路径读取。

#### 七项修复的隔离组合验证（2026-11-25）

- [#25](https://github.com/lse872317312010/QuantOs/pull/25) 为验证专用草稿，禁止直接合并。基线 `cc1e40b9cdc5a8ba238b8800c77ec59c68293ed6`，组合提交 `94fcc3ed974164d16de49e2a78a370f711412df0`，tree `cde5e1b0b2dd70fcfc645dd51c61812f8c640a9c`；精确来源 head 在 #25 描述中。
- [PR CI 45546031600](https://github.com/lse872317312010/QuantOs/actions/runs/45546031600) 的 test job 日志确认 Ruff 全通过、pytest **143 passed, 27 warnings in 4.39s**；[push CI](https://github.com/lse872317312010/QuantOs/actions/runs/45546004139) 亦成功。[Codex 对该精确提交的审查](https://github.com/lse872317312010/QuantOs/pull/25#issuecomment-7152752201) 完成且无发现，#25 无 inline review threads。独立 CI 与隔离组合 CI 成功不等于 main 已集成；警告当时尚未分类（后续日志核验见下文），不视为已解决。
- 组合契约：#19 的未来行情异常和 #24 的结构化拒绝统一为 UNAVAILABLE，复用 #19 `as_utc` 和 #21 `DataQualityReport.unavailable`；测试要求不可用状态及空时间/新鲜度/完整性，而非静默接受未来数据。#24 旧审查线程在该次组合时尚未关闭（后续已核实解决，见下文）。
- **正常集成计划（提案，尚未执行）：** 先由所有者采纳 #17；普通代码 PR 按最新基线、适用权限、精确提交 CI 与审查门槛逐一处理。#22 以 #21 分支为 base，先核验 #21 的合并结果，再审查 #22 的目标 base 与增量差异，避免重复引入。#19/#24 以及其他重叠文件按 #25 已验证的契约在正常 PR 上协调；每次重新取 head/base、复验合并差异并请求必要的最新审查，不能以 #25 的测试替代新提交检查。不直接合并 #25、不强推、不批量无条件合并。最终对 main 运行适用全套 CI 并核验集成契约、历史产物隔离及剩余 P0 时间/交易日历与治理验收。
- 本轮仅记录验证证据及集成计划；无实际行情、正式预测、前向案例或投资有效性证据；无新增运行依赖、权限、费用或服务。回滚文档更新用正常 revert；#25 保持隔离。

#### 叠加集成与借用成本（2026-11-25 后续核验）

- [#26](https://github.com/lse872317312010/QuantOs/pull/26) 是面向 #19 的正常增量 PR，head `5abaa5b4876a1f1ad870d3811c95e1348d780557`，base `fix/p0-review-risk-gates`。统一 #19/#24 的未来行情拒绝契约，保留诊断与空指标；[精确 head CI 45559797266](https://github.com/lse872317312010/QuantOs/actions/runs/45559797266) 实际日志为 Ruff PASS、86 passed、14 warnings；[Codex](https://github.com/lse872317312010/QuantOs/pull/26#issuecomment-7154682424) 同 SHA 无发现。#24 原审查线程 [4689658983](https://github.com/lse872317312010/QuantOs/pull/24#discussion_r4689658983) 经 GraphQL 核实已解决且过时。#26 描述记录七项真实合并历史重放与 #25 tree 一致、143 项本地测试通过；本轮未独立重跑该本地实验。
- [#27](https://github.com/lse872317312010/QuantOs/pull/27) 是新增 C05/C09/C10/C14 正确性修复，head `e19c024eadc3cf6fe5b0b2ceca52e473513ce0d0`，base `fix/p0-realized-label-boundaries`（#18）。空头借用成本依实际退出时间而非请求期限；正费率缺失/冲突时间不填虚构成本，未匹配样本继续计入覆盖率分母。[精确 head CI 45560576232](https://github.com/lse872317312010/QuantOs/actions/runs/45560576232) 实际日志为 Ruff PASS、78 passed、16 warnings；[Codex](https://github.com/lse872317312010/QuantOs/pull/27#issuecomment-7154789875) 同 SHA 无发现。PR 描述另记录本地八项修复组合 tree `ee1d6a6cd3ccebd7fcf5a80223b3e329c5fb0893`、148 passed、28 warnings，以及离线合成报价 CLI 复验；本轮未独立重跑、未取得该组合的远端 CI，不把它写为八项远端组合验收。
- [#25 CI 日志](https://github.com/lse872317312010/QuantOs/actions/runs/45546031600) 的 27 项 pytest 警告已按原始日志分类：24 项 pandas Series.values 的时区数组行为弃用（test_research 20、test_validation 4）；3 项 Polars grouped join_asof 无法自动检查排序。#26/#27 的最新日志重复出现这两类，另有 GitHub Actions Node.js 20 弃用提示（不计入 pytest warnings）。后续需定位 pandas 调用栈，验证 UTC 时间和 DST 边界不受未来版本变更影响，并针对每组时间单调性、乱序输入和等时刻匹配建立行为测试；不能仅屏蔽警告。CI runner 兼容性更新独立处理。不把警告分类等同于问题修复。
- 正常集成计划更新（仍待治理采纳及授权）：#26 先在实际 #19 base 上复核，按保留真实合并历史的方式集成 #19/#24 的契约协调；避免 #24 重复引入。#27 先在 #18 base 上复核，依赖 #18；#22 依赖 #21。保留 #16/#20 独立路线，任何 base/head 更新后重新验证实际增量与审查。禁止直接合并 #25；不以此前七项验证替代八项最终主线验证。#17 上一 head `dcb0b046b192d5807b6a32af0248ce19e5d08ddd` 的 [CI](https://github.com/lse872317312010/QuantOs/actions/runs/45553095309) 与 [Codex 复审](https://github.com/lse872317312010/QuantOs/pull/17#issuecomment-7153726330) 已通过；本次文档更新须重新核对新 head。
- 历史影响：除原时间/数据质量问题外，正费率延迟退出的旧空头成本及其派生验证和晋级指标须保留旧版并从可验证行情在新目录重算；无真实源则继续未核验。#26/#27 均未合并，未修改依赖、数据权限、资金权限、费用或部署。本次只更新证据与待办，回滚为普通文档 revert。P0 尚未正式验收。

#### 交易日、匹配确定性与历史键审计（2026-11-25 后续核验）

- [#28](https://github.com/lse872317312010/QuantOs/pull/28) 依赖 #16，head `f5cdc76e6ea3a9792cd56daf431d3f67a7260d47`。复用 exchange_calendars 表达实际交易时段收盘期限，[精确 head CI 45566254147](https://github.com/lse872317312010/QuantOs/actions/runs/45566254147) 成功，Codex summary 对同一 SHA 完成且无发现。PR 报告九项本地组合 162 passed，仍不是最终主线验证；未在本轮重跑该组合。
- [#29](https://github.com/lse872317312010/QuantOs/pull/29) 依赖 #27（继承 #18），head `ddc0889ea2428c987aaf1d0a9881222d8e5b936d`。在 grouped join_asof 前拒绝同标的同毫秒的重复键，保留跨标的同时间合法性、乱序输入排序及无匹配标签；不任意决定同键报价的先后。此次核对 [CI 45567757759](https://github.com/lse872317312010/QuantOs/actions/runs/45567757759) 的 job 139046629367 原始日志：Ruff PASS，**81 passed, 25 warnings in 6.73s**；[Codex 同 SHA 审查](https://github.com/lse872317312010/QuantOs/pull/29#issuecomment-7155813805) 完成无发现。20 项 Pandas4Warning、5 项 grouped join_asof 无法自动核验排序警告仍存在。与 #21 的实际接收时间字段合入时须再验证，不将重复键拒绝等同于上游警告修复。
- [#30](https://github.com/lse872317312010/QuantOs/pull/30) 为独立只读历史键核查工具，基于 main，head `8581efd7587700d868f451cb1dbb6f4507d36fdb`；复用已有 signals.parquet、Polars 与 SHA-256，区分冲突/重复/未知，不修改源文件。此次核对 [CI 45577525415](https://github.com/lse872317312010/QuantOs/actions/runs/45577525415) job 139079035466 原始日志：Ruff PASS，**76 passed, 14 warnings in 7.70s**；[Codex 同 SHA 审查](https://github.com/lse872317312010/QuantOs/pull/30#issuecomment-7157216424) 无发现。PR 报告通过旧版分析入口生成合成归档、安装 wheel 实际运行、比对 34 个既有文件哈希及专项 10 项测试；本轮未独立重跑这些本地实验。该工具只核查保留行的键，不能证明原始数据完整、接收时间可用或历史收益有效。
- 历史产物操作顺序（待实际获准产物）：先保存输入版本和旧报告，再按独立运行目录使用 #30 的只读命令审计；重复、缺档、未知或损坏均不得证明可采用，保留审计 JSON 与输入 SHA。即使未发现重复，仍需核查接收时刻、源许可、成本和真实标签边界；有可靠原始观测及版本时才在新目录重算，否则保留未核验状态。仓库尚无已核实的真实历史归档，本次没有执行真实历史重算。
- 正常集成依赖补充：#16 → #28；#18 → #27 → #29；#30 独立，#19 → #26、#21 → #22 依旧。#29/#21 重叠时序语义需在真实目标 base 上协调；#30 的入口/文档也需与最终树验证。#25 仍仅验证七项，不直接合并；已有组合记录不覆盖新增 #29/#30。所有新增 PR 仍开放；不在治理采纳前合并。#17 上一精确 head `57d694edb925763a4b646af252f86209f3016383` 的 [CI](https://github.com/lse872317312010/QuantOs/actions/runs/45564693029) 与 Codex summary 同 SHA 均通过；本次文档变更需要新的 CI/审查。
- 下一独立审计重点：定位 pandas 时区弃用调用栈，验证 UTC 转换与交易日语义，避免直接屏蔽警告；检查最终组合的匹配与真实接收时刻语义。无新依赖、数据权限、费用、部署或资金权限；文档可正常 revert。P0 未正式验收。

历史采集和原研究结果需保留原版本。只有能核实接收时刻的 CSV 才能在新目录重建对应的 Parquet、holdout、bootstrap、walk-forward 和 promotion 产物。旧 REST 批次缺少逐响应接收时刻，旧晋级表缺少生成时刻，旧决策日志也可能缺少风险核验记录。这些产物保留为未验证历史。仓库未跟踪真实采集，尚无可重算的真实样本或前向案例。各 PR 记录了独立回滚方式。

2026-11-25 核验时，`main.protected=false`，对该分支生效的规则列表为空。2026-11-26 在 #17 合并后再次查询，分支保护标记仍为 `false`，包含父级规则集的仓库查询返回空列表。后续启用保护需由维护者配置并核验。[分支状态](https://api.github.com/repos/lse872317312010/QuantOs/branches/main) · [仓库规则集](https://api.github.com/repos/lse872317312010/QuantOs/rulesets?includes_parents=true)

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
| 1 | 所有者审核并采纳宪法 | #17，C15 | 已合入主线并生效 |
| 2 | 修复预测登记的 UTC/DST 时序并采用交易日收盘期限 | #16、#28 的合并提交和主线 CI | 两项均已合并，见[主线记录](#p0-mainline) |
| 3 | 审计既有研究、风险与快照 | [行情主线记录](#p0-mainline)、[研究与风险主线记录](#p0-closeout) | 工程修复已全部合入，主线 233 项通过（含 #44 移植的时序回放覆盖）。单独复验时序与故障 14 项通过。历史归档范围待确认。 |
| 4 | 接入首个获准资料并建立来源版本记录 | P0；P1；[Issue #23](https://github.com/lse872317312010/QuantOs/issues/23) | FOMC 候选来源预研，未取得实际配对行情；未验收 |
| 5 | 知识检索、假设登记及持久化 | P1→P2→P3 | 未验收 |
| 6 | 可复现实验及真实预测到期复盘 | P4→P5 | 未验收 |
| 7 | 低负担运行与多市场/界面扩展 | P6；明确授权 | 未验收 |

工程修复与治理提案分别交付。P1 的验收仍需一份真实获准原文、对应行情和人工核对记录。

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
