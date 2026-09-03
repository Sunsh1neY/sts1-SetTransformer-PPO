# 决策日志

> 用途：记录所有已裁定决策及其**推翻条件**。推翻已有决策前，必须先在文末"决策变更记录"登记；未登记的推翻视为违规。
> 来源：`spec-v4.md`（2026-09-01 定稿），2026-09-03 建仓库时入账。
> 元规则（v4 §10.3）：任何单一问题连续投入超过 3 天无进展 → 强制停下，写下卡点、已试方案、两个**不同**方向，选更不一样的那个。

## 2026-09-03：v4 定稿 12 项裁定入账

### D1 时间预算：18 周 × 30h = 540h（2026-09-01 起算，2027-02 初出发，扣缓冲 4 周）

- 理由：出发日期是硬约束；v3 的 40h × 26 周假设不成立。
- 推翻条件：连续两周实际投入 < 20h，或出发日期提前 → 立即按 §10 降级路径执行，不等下一个 Gate。

### D2 环境来源：自写 Python 模拟器；规格用 STS1；runlogger 日志作正确性 oracle

- 理由：训练通道需要可控、可复现、高吞吐；STS2 生态不成熟（v4 §0.3）。
- oracle 已定位：`colinking/runlogger`（GitHub），逐行 JSON 带 `_type` 字段；beta 期格式可能 breaking change，拉取时锁定版本；游戏自身可复现性 bug 需配 Determinism Fix。
- 推翻条件：日志按 §5.2 子集过滤后无可回放片段（覆盖不足）→ oracle 降级为 sts_lightspeed 差分测试 + 纯单元测试，在此登记后执行。

### D3 技术中心：先 A（Set Transformer + PPO）→ 后 B（Decision Transformer），A/B 对照即产出

- 理由：两者嵌套（B 的 state token = A 编码器输出），先 A 后 B 省一次重写；真实目标是理解 Transformer 原理。
- 推翻条件：Gate 3 触发 → PPO 出局，A 阶段改 BC + Set Transformer 监督学习，架构对照保留；B 阶段不受影响。

### D4 机制范围：两步扩容（第 1-4 周最小切片 → 第 5 周起中等档），不做完整 Act 1

- 理由：回放对拍的验证强度随机制范围一起增长（v4 §5.2）；最小切片先过 Gate 1。
- 推翻条件：Gate 1 失败 → 砍掉中等档，锁死最小切片到项目结束（§10）；第 5 周 HF 卡表抽查不过关 → 卡表改手工整理。

### D5 观测/动作表示：环境返回结构化 dict；FlattenWrapper 与 TokenWrapper 同源派生；动作扁平 `(槽位, 目标)` + mask

- 理由：同源派生保证 MLP 与 Transformer 特征一致，对照实验才干净；扁平动作让 DT 的 action 天然是单个离散 token（v4 §4.3）。
- 推翻条件：第 11 周 token 编码就绪后评估 pointer head（未决事项 U1）；扁平动作本身不翻案。

### D6 v3 处置：冻结为愿景文档；继承与规模无关的设计约定；放弃规模主张

- 推翻条件：本项目 18 周完结且有富余，STS2 属于**下一个项目**，不在本项目内解冻。

### D7 奖励：胜负 + 剩余血量连续回报，加 potential-based 回合惩罚；λ=0.5 起；A/B 共用同一标量

- 理由：DT 的 return-conditioning 需要回报有分辨率，稀疏 ±1 会让条件变量退化（v4 §4.4）；potential-based shaping 保证最优策略不变。
- 推翻条件：第 5-6 周校准 λ 一次，之后锁死；监控发现主动送死率异常（奖励黑客）→ 回查 Φ 与回合惩罚定义——这属于 bug 修复，仍需在本日志登记。

### D8 评估协议：1000 隔离种子、按遭遇类型分桶、配对 bootstrap 95% CI、附效应量

- 理由：STS 种子间方差极大，非配对比较检不出真实差异（§6.2）；回报双峰，t 检验正态假设不成立（§6.5）。
- 落地：`eval_seeds.json` 已生成（sha256 `38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c`），由 `scripts/make_eval_seeds.py` 按固定规则生成（seeds = 0..999，非随机抽取，可审计）。
- 推翻条件：`eval_seeds.json` 提交后不可变——变更即作废全部历史结论。分桶后某关键桶样本不足，允许单独加采样（预授权，无需登记）。

### D9 正确性验证：单元测试 + 日志回放对拍；sts_lightspeed 差分测试为 stretch

- 推翻条件：第 2 周 `sts_lightspeed` 半天试 build 失败 → 立即放弃并在此登记原因，不允许超过半天。

### D10 工具链：CleanRL 单文件 PPO 起点；架构手写；YAML + dataclass + argparse；W&B 或 TensorBoard

- 理由：PPO 对实现细节极度敏感，无抽象层才能逐行看懂（v4 §8）；架构手写是学习目标本身。
- 推翻条件：CleanRL 与结构化 dict obs + mask 的冲突过大 → 允许参考其结构自写训练循环（保留逐行可读性），登记后执行；W&T vs TB 见 U2。

### D11 止损：日历闸门 + 指标门槛，谁先触发算谁；降级路径预先写死

- 推翻条件：仅当门槛本身写错（元错误）才可修订，修订需登记并说明为何排期时未发现。

### D12 真实目标：通过工程实践理解主流 Transformer 技术原理；游戏是载体

- 理由：所有降级路径都服务于此——Gate 3 降级后架构对照依然成立（§10.1）。
- 推翻条件：无。这是锚点，其余一切可为它让路。

### D13 反编译查阅政策（2026-09-03，用户确认）

- 裁定：**非目标维持**——反编译不作为获取游戏逻辑的主路线；允许在规格争议仲裁时**定点查阅**反编译源码；红线：**不得照抄反编译代码进模拟器**（保住 lightspeed 差分与对拍体系的独立性）。
- 使用阶梯：wiki / 社区文档 → lightspeed 源码 → 反编译 Java → runlogger 日志兜底。
- 存放（用户指定）：反编译产物放 `reference/sts1-decompiled/`（gitignore，不入库——版权风险只在公开分发，本地查阅无风险）。生成命令见 `reference/README.md`。
- 首例仲裁已立案：Vuln/Weak 乘法先后（mechanics.md §4 出现矛盾证据），第二档入库前终审。
- 落地进度：游戏本体已定位 `E:\SteamLibrary\steamapps\common\SlayTheSpire\desktop-1.0.jar`；jadx 未下载，首次仲裁前生成即可。

### D14 RNG 实现：复刻 java.util.Random，弃用 numpy PCG64（2026-09-03，第 2 周 rng.py 落地前裁定）

- 起因：用户提问「Python 写的随机数和游戏 Java 的一样吗」——不一样（48-bit LCG vs PCG64，同 seed 序列毫无关系），且直接威胁日志对拍与 lightspeed 差分的可行性，故提前裁定。
- 裁定：环境内一切随机性由 `sts/env/rng.py` 的 `JavaRandom` 逐位复刻（javadoc 公开算法：LCG 核心、nextInt 拒绝采样消除模偏差、nextDouble 53 位尾数）；4 条流**全部用同一 combat seed 初始化**——忠实游戏"每层同种子重建全部战斗流"的结构，流间相关性是真实物理，不"改良"。
- 已知向量锚定逐位正确性：`Random(42).nextInt() = -1170105035`、`Random(0).nextDouble() = 0.730967787376657`（两者均为广泛引用的公认首值，实现命中）。
- 理由：① 第 3 周日志回放要求「同 run seed + 同动作 → 同状态」，随机序列必须与游戏逐位一致；② U6 lightspeed 差分同样要求 seed 对齐（其 100% RNG accurate 即 Java LCG）；③ 复刻成本一次约 40 行，有公开测试向量可锚定。
- 推翻条件：仅当反编译仲裁（D13）发现游戏实际使用的随机原语超出 javadoc 语义（如自研 PRNG）时重审。numpy 退出环境内使用；训练/统计侧随机性第 7 周起归 torch 生成器。

## 未决事项（v4 §12，不阻塞开工）

| # | 事项 | 何时定 | 默认 |
|---|---|---|---|
| U1 | 动作头：扁平索引 vs pointer head | 第 11 周 | 先扁平 |
| U2 | W&B vs TensorBoard | 第 7 周首次训练前 | 任选，接口封一层 |
| U3 | 中等档卡表来源核实 | 第 5 周 | HF `t22000t/slay-the-spire-1-cards` 抽查 5-10 张后决定 |
| U4 | `sts_lightspeed` 是否纳入 | 第 2 周 | **已克隆**至 `third_party/sts_lightspeed`（commit `7476a81`，2026-09-03）；剩余：半天试 build，卡住即弃 |
| U5 | λ 终值 | 第 6 周 | 0.5 起，校准后锁死 |
| U6 | oracle 主通道：runlogger 日志 vs lightspeed 差分 vs 双轨 | 第 2 周（U4 试 build 后） | 双轨：lightspeed 日常高吞吐差分，runlogger 留作真值校准抽查 |
| U7 | ~~反编译源码查阅政策~~ | **已裁定 → D13（2026-09-03）** | — |

## 附 B 未核实事实销账表（v4 附 B → 实测后填）

| # | 事实 | 状态 | 核实记录 |
|---|---|---|---|
| 1 | runlogger 的局数、卡牌覆盖、schema | 部分（2026-09-03） | 游戏本体已定位 `E:\SteamLibrary\steamapps\common\SlayTheSpire\`（含 `desktop-1.0.jar`）；**runlogger mod 未安装**（无 `runlogs/`），需创意工坊订阅 + 打几局 Ironclad（第 3 周前）；游戏自带 `runs/` 有历史对局记录（含 IRONCLAD 目录，后续抽查是否可用于对拍） |
| 2 | sts_lightspeed 的 API / 构建 / 覆盖 | 待实测（第 2 周） | 仓库已定位：`gamerpuppy/sts_lightspeed`（C++17 + pybind11，自称 100% RNG accurate，覆盖 Ironclad 全卡 + 全部敌人；作者用 mingw64/CLion2021 构建，Windows 编译有已知摩擦，Reddit 有失败案例）→ 第 2 周半天试 build |
| 3 | HF 卡表数值准确性 | 待实测（第 5 周） | — |
| 4 | 纯 Python 模拟器吞吐 | 待实测（第 4 周 Gate 1） | — |
| 5 | determinismfix 是否必需 | 待实测 | runlogger README 明言游戏有可复现性 bug、需装 Determinism Fix，基本确认必需 |

## runlogger 侦察记录（2026-09-03）

- 仓库：https://github.com/colinking/runlogger （Steam 创意工坊订阅安装）
- 日志格式：每行一个 JSON 对象，含 `_type` 字段标明对象类型
- 路径：进行中的 run 在 `saves/IRONCLAD.run.log`；完成后改名并移入游戏目录下 `runlogs/<角色>/<时间戳>.run.log`
- 风险：mod 处于 beta，格式可能 breaking change → 拉取日志时锁定 mod 版本并记录
- 第 1 周剩余动作：本机游戏是否已装此 mod；统计 `runlogs/` 实际局数、卡牌覆盖；schema 快照存 `docs/` 或 `research/`
- 核验来源：runlogger GitHub README（2026-09-03 抓取）

## 决策变更记录

（本节起为空。任何对 D1-D12 的推翻在此追加：日期 / 变更内容 / 触发条件 / 新决策要点。）
