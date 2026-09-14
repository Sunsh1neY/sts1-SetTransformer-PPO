# AGENTS.md — STS RL Agent 工作区

## 工作区性质

- 当前为 **STS RL Agent 执行工作区**，唯一执行依据是 `spec-v6.md`（2026-09-08 双任务奖励修订；不重置原排期）：锁定的 `sts_lightspeed` C++ headless STS1 Ironclad 战斗后端（Python 保留教学/规范层） → 随机/规则两条基线 → A 阶段 Set Transformer + PPO → B 阶段 Decision Transformer，A/B 对照即产出。真实目标：通过工程实践理解 Transformer 原理，游戏是载体。
- 全部文档与代码注释用中文；文件名用英文小写 kebab-case。
- 目录名 `sts2` 是 v3 时代（STS2 方案研究）的历史遗留，不改名；实际规格来源是 **STS1**。
- 排期与止损以 `spec-v6.md` §9/§10 为准；学习目标与方法见 `docs/learning-path-v2.md`，`学习路径.md` 为旧版历史存档。

## 当前进度（2026-09-14：A 路径成为 main 主线）

- 用户依 I5 明确 A 路径是后续主要方向，已合入归档的模型、Agent、独立采集池和联合 PPO。默认链路为 scripts/run-a-path-ppo.py → sts/train/apath.py → sts/env/apath.py → 全卡 C++ 后端；模型为 sts/models/apath.py。后续功能与学习文档沿此链路推进，旧 Unified 66 动作及 Comparison/MLP 保留历史身份。
- 维持四层 SAB、64 维、4 头、FF128、单 seed PMA、来源与条件目标两阶段分布、联合 log-prob/PPO 和精确熵。来源组均匀采样，完整 rollout 全局 shuffle，内容分组只用于诊断。
- 全卡 A20 环境支持 75 类/150 版本、第一二幕 44 遭遇及已有第三幕 MAW/TRANSIENT；训练仍限独立注册池的 39 卡组、两条件、五遭遇。训练池已绑定 main 新环境指纹，未扩大来源或改奖励。
- 主线整合与实际验证见 docs/a-path-main-integration-report.md。旧检查点、辅助目录和旧分支历史保存在 reference/desktop-repo-archive-20260914；恢复说明见 docs/desktop-repo-cleanup-2026-09-14.md。旧桌面路径不再有效，旧检查点不可跳过指纹校验续训。
- 本次合并只进行短工程验证，不自动重启四小时训练或扩池；eval_seeds、历史实验和原交接说明保持不变。

## 2026-09-13进度（环境集成历史）

- 独立环境集成完成：1244项CPU回归及独立C++夹具1项通过，见docs/environment-integration-report.md。
- 当前按决策I0与a-path继续四层64维SAB＋PMA、两阶段来源/目标Pointer及联合PPO。工程后受限训练，尚未宣称完成。
- 用户于2026-09-13追加授权：先提交并push当前基准，再继续A路径；每个里程碑报告完成、问题和未完成项，需要用户裁决时暂停相关工作。保留旧实验和辅助worktree。

## 2026-09-12历史进度

- 本轮固定环境M3工程已完成：真实中途27种卡组、5遭遇、两条件，comparison-battle-v2；逐牌64实体、57触发容量外部截断、8张增长余量，MLP/Set使用相同信息和66动作。
- GPU完成MLP/Set各2组，每组138轮/70656transition，总训练及评估1097.41秒。四组相对初始策略的开发配对改善区间下界均大于0；Set−MLP区间均含0，不宣称架构优势。报告见docs/comparison-ppo-report.md。
- 633项完整CPU回归、15项CUDA环境相关测试、GPU精确续训预检及4份最终checkpoint实际恢复通过。训练中1次容量截断不计失败；评估全部自然终止。GPU入口为.venv-gpu/Scripts/python.exe。
- 后续MLP在此范围冻结，扩展环境只推进Set。全卡审计、扩大环境、正式Gate及用户独立学习理解仍另行验收，不把本轮结果推广为总体泛化。
- 工作树仍有大量未提交工程及文档；保留旧实验和用户/其他agent修改，不能重置。以下旧进度保留历史身份。

## 2026-09-11进度快照（历史）

- 最新提交基线为 `80d2340`；其中已包含 S4 三初始化诊断、S5 最小可学习检查点冻结，以及 PPO 训练观察学习记录和固定状态诊断脚本。
- M0 / D25 S1–S5 工程已完成：三组各完成 256 轮、262144 个 transition；S4 三组 300 局开发配对回报差 CI 下界均大于 0；S5 恢复、最终 checkpoint、评估和 278 项完整回归已记录。证据见 `docs/ppo-s4-report.md`、`docs/ppo-s5-freeze.md`。
- 当前不宣称正式 Gate 2、Gate 3、中等环境泛化、Set Transformer 完成或跨更大任务稳定性；负 `explained_variance` 仍是诊断项，原因未定。
- M1 候选审计已于 2026-09-11 收口：覆盖正版 JAR 的 75 个 Ironclad 类、150 个卡牌版本，分类为 A6/B123/C16/D5；`docs/m1-candidate-batches.md` 提供 35 类实施候选，`docs/m1-numeric-evidence.md` 补齐原十张正版数值定位。正式白名单、reset 配置、扩展卡行为测试和 M2 契约仍未完成。
- M2–M8 尚未完成；当前 31 位动作协议不变，扩容不得绕过二次选择、容量、可见字段和版本契约。
- PPO 训练观察学习的工程展示已完成：TensorBoard 续训日志、固定 seed `900000` 的 32/128/256 概率对照及学习记录均已落盘；用户独立理解复述仍另行验收。
- 当前工作区保留未提交的 M1 进度：`docs/decisions.md` 的 S5/M1 补记，以及 `docs/ironclad-card-audit.md`、`docs/ironclad-card-audit-review.md`、`docs/m1-candidate-batches.md`、`docs/m1-numeric-evidence.md`；不得重置、覆盖或把候选审计当作正式白名单。

## 文档层级（权威顺序）

| 文件 | 地位 |
|---|---|
| `spec-v6.md` | **当前唯一执行依据**（2026-09-08 双任务奖励修订；不重置原排期），改动须先过 `docs/decisions.md` 登记 |
| `docs/decisions.md` | 决策日志：裁定 / 理由 / 推翻条件；推翻既有决策必须先在此登记 |
| `docs/mechanics.md` | 结算顺序书面规格，`tests/test_ordering.py` 的唯一依据；与日志对拍冲突时以日志为准并修订本文档 |
| `docs/learning-path-v2.md` | 学习目标、三种思维、双环推进与理解验收方法；不覆盖 v6 的执行范围、排期和 Gate |
| `学习路径.md` | v1 历史存档，已由学习路径 v2 重写替代 |
| `spec-v5.md` / `spec-v4.md` | 冻结历史方案；历史验收仍保留当时出处 |
| `spec-v3.md` / `spec-v2.md` / `spec.txt` | 冻结愿景稿（STS2 / A10 / 完整 run 不进入本项目排期），仅供对照，勿据此实现 |
| `research/` | v3 时代 STORM 研究报告与项目尽调，随 v3 冻结 |
| `docs/report.md` | 第 17-18 周产出，尚不存在 |

## 执行红线（继承自 v4、由 spec-v6 维护，勿翻案）

- `eval_seeds.json` 提交后**不可变**；评估 seed ∈ [0, 1000)，训练 seed ≥ 100000；每个 run 记录其 sha256。
- seed 不进状态编码，只保留给环境复现。
- 动作索引指向手牌槽位（槽位按抽牌顺序确定分配）；token 特征只用语义，绝不编码槽位号。
- 合法动作列表由环境直接给出，模型不猜合法性；掩码在 softmax 之前施加，梯度用掩码后分布计算。
- 同一任务内 MLP-PPO、Set-PPO 与 DT 必须使用同一逐步 reward、γ 和完整真实 RTG；`battle_reward_v1` 与 `run_reward_v1` 不得混用，改动须新建奖励版本并从可验证字段重算数据。
- 当前 `battle` 首次胜利奖励为 `1+0.5*h_exit`；未来 `run` 仅首次最终通关得1。普通战斗胜利不得终止全局 run；完整 RunEnv 未实现时拒绝正式 run 训练。
- 真终止不自举；外部截断使用 reset 前最终观测自举但 GAE 不跨 reset。异常轨迹不伪造成失败0；v6 基线固定 β=0。
- Gate 触发即执行预写死的降级路径（§10），不当场重新谈判；任何单一问题连续 3 天无进展，按 §10.3 元规则强制停下换方向。
- 第 17-18 周不写新功能。
- 反编译源码只作规格争议仲裁（D13），不得照抄进模拟器；产物放 `reference/`（gitignore）不入库。
- 仓库骨架按周生长：不预建空文件与空目录（掩盖进度）。

## 文档与事实规范

- 事实主张（游戏机制数值、论文结论）须有一手来源；尚未核实的事实显式标注 `[未核实]`（v6 附 B，按证据持续销账）。
- 引用登记沿用 `research/sts2-a20-decision-model-sources.md` 的编号日志格式（可信度等级 + 核验日期）。

## v3 时代历史裁定（随 spec-v3 冻结，不再指导执行）

以下条目在新排期中均不生效，与 spec-v6 冲突时一律以 v6 为准：A10 目标（非 A20）、M0-M4 里程碑顺序、反编译 sts2.dll 主路线、v1→v2 五处结构性变更、卡组-地图双塔评估器、KL 锚定退火、AlphaStar Unplugged 精读待办。
