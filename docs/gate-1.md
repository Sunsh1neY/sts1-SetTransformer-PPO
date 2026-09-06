# Gate 1：环境基础门槛验收

验收日期：2026-09-05。规格依据：`spec-v4.md` §5.1、§9、§10，及
`docs/decisions.md` D20。当前结论：**Gate 1 通过，不触发 §10 的降级路径。**

> 版本说明：本文记录 2026-09-05 的计数版输入历史验收。2026-09-06 按 D24 迁移为
> 逐牌实体 V2 后已重新完成专项、确定性、10000 场稳定性与四路径性能验收，结果见
> [`entity-foundation-report.md`](entity-foundation-report.md)。D24 新结果同样通过，
> 本文旧 wrapper shape 与旧性能数字不再描述当前接口。

这个结论只表示当前锁定的 A0 最小战斗切片满足五项基础门槛，不表示模拟器已经与
正版 STS1 全机制、全字段或全部战斗逐步一致。有限日志中的实际差异和未验证范围
仍然有效，不能被稳定性或性能结果覆盖。

## 1. 五项 Gate 结果

| # | Gate 1 项 | 状态 | 核心证据 |
|---:|---|---|---|
| 1 | 现有 runlogger 片段有限字段校准 | 按 D20 完成 | 一致、差异、失败与未验证项分开记录；未扩日志工具 |
| 2 | 结算顺序单元测试全过 | 通过 | `tests/test_ordering.py` 25 passed；正式 C++ 接口测试 25 passed；无 skip |
| 3 | 同 seed 轨迹一致 | 通过 | 三遭遇各 20 场，四路径各重跑两次；路径内及跨路径语义差异均为 0 |
| 4 | 随机策略 10000 场稳定 | 通过 | 每条路径 10000 场、184117 步；异常、非法动作、硬超时、奖励错误均为 0 |
| 5 | 单核吞吐 ≥ 2000 steps/s | 通过 | raw / dict / Flatten / Token 中位数为 15690 / 7923 / 5910 / 5749 steps/s |

双 wrapper 是 Week 4 工程交付，证据见本文第 6 节；它不被伪装成规格之外的第六项
Gate 1 门槛。

## 2. Gate 1.1：有限日志校准

本项按 D20 的修订口径验收：完成现有片段的有限校准和诚实分类，不要求日志未提供的
字段匹配，不新增日志 mod，也不建设全机制逐状态对拍系统。

### 已比较且一致

- Python 教学回放中，第二份 Jaw Worm 日志的 12 个已记录快照字段匹配。
- Python/C++ 差分探针的 12 个 seed 中有 2 个实际匹配；这里只把这 2 个计为匹配。

### 已比较且存在差异或失败

- C++ 日志回放通道的两份日志共 `17 / 11` 个快照均报告差异。日志玩家初始 HP 与
  上限为 88，`ConsoleSimulator` 为 80，后续 HP 持续相差 8；回放初态尚未对齐，
  根因未定。该结果不能记为通过，也不能直接归因于正式 `IroncladBattleEnv` 的战斗
  规则。
- Python/C++ 差分探针另有 6 个 seed 因进程退出码 3 的断言失败。进程异常按失败
  记录，没有并入匹配数。

### 跳过与未验证

- 差分探针另有 4 个 seed 超出当前机制范围，单列为跳过。
- Python 教学回放缺少终局一步，终局未由该日志片段验证。
- 日志 schema 未记录或时点无法对齐的 HP、block、buff 等目标字段不补造、不默认
  一致；runlogger 的完整局数、卡牌覆盖和全机制准确性仍未验证。
- STS1 自身复现性风险及 `determinismfix` 的实际必要范围仍未完成实测销账。

按 D20，日志字段或片段覆盖不足不单独触发降级。后续扩容若发现会改变动作、奖励、
确定性或 A/B 实验结论的差异，须针对该差异修复并补证据。

## 3. Gate 1.2：结算顺序与正式扩展

2026-09-05 在当前工作树执行：

```powershell
python -m pytest -q tests/test_ordering.py
# 25 passed in 0.17s

python -m pytest -q tests/test_cpp_env.py
# 25 passed in 0.05s

python -m pytest -q tests/test_ordering.py tests/test_cpp_env.py
# 50 passed in 0.33s
```

`test_ordering.py` 依据 `docs/mechanics.md` 检查状态机结算顺序；`test_cpp_env.py`
直接导入并执行正式 C++ 扩展，覆盖布局契约、动作合法性、确定性、奖励、硬超时、
范围限制和牌堆守恒等接口回归。本次没有 skip，不能归因于扩展未构建。

正式扩展：

- 文件：`third_party/sts_lightspeed/build/slaythespire.cp313-win_amd64.pyd`
- sha256：`b41522e6f9df807bb5527f07aecd477c569f70b42c732a7135fe6e8aab98c114`
- 上游提交：`7476a81954020087da31d41d16fddf475746ec2d`
- 项目适配补丁 sha256：
  `6753a1a7e4f131461de8ef2e7014445ded4527e38ec68fe3ff3d734ae708a511`
- 构建：CMake 4.4.2、MSYS2 g++ 16.2.0、Ninja 1.13.2、Release、CPython 3.13.2

## 4. Gate 1.3：确定性

使用 T5 同一配置集，按 Jaw Worm / Cultist / 双虱各 20 场分层取 60 场。raw
pybind、规范 dict、FlattenWrapper、TokenWrapper 四条路径各自从相同环境 seed 和
Agent seed 开始，每个 path-episode 重跑两次。

逐步比较动作前及 `step` 返回后的观测、完整 31 位 action mask、实际动作、奖励、
`terminated/truncated` 与排序后的允许 `info`。固定序列化显式规定字段顺序、shape、
dtype 和小端字节序；时间戳和机器信息不进入确定性载荷。Flatten 与 Token 的原始表示
不同，只比较各自路径内字节及跨路径对应的规范语义。

- 路径内重放失败：0。
- 跨路径规范语义、mask、动作、奖励、标志与 info 差异：0。
- 结论：本门槛通过。

## 5. Gate 1.4–1.5：稳定性、奖励与性能

可复跑命令：

```powershell
python scripts/run_week4_t5.py --episodes 10000 --repeats 3 `
  --warmup-episodes 100 --determinism-episodes 60 `
  --output build/week4-t5-acceptance.json `
  --worktree-patch build/week4-t5-worktree.patch
```

唯一配置为 seed `100000..109999`，三遭遇分配 `3334 / 3333 / 3333`。每条路径
重放全部 10000 配置；Agent seed `20260905000..20260914999` 与环境 RNG 分离，
四条配对路径从相同 Agent 状态开始。正式 Agent 依 D23 产生掩码后的
`probabilities[31]` 并在内部抽样 `action:int`；runner 无抽样 RNG、不重算合法性。

四条路径每轮统计完全一致：

- 10000 场、184117 步、8711 胜 / 1289 负；
- 异常 `0 / 10000`；
- 非法动作 `0 / 184117 = 0%`；
- 硬超时 `0 / 10000 = 0%`；
- D18/D20 奖励检查失败 0，累计奖励 `11403.574952483177`。

压力运行没有实际出现硬超时，因此只能报告触发率为 0；“触发后终止、判负、奖励为
0”由第 3 节的定点 C++ 单元测试验证，不能用“未出现”替代该分支证据。

性能限制常见数值库线程为 1；每路径先预热 100 场，再以完整 10000 配置重复三次。
wall-clock 包含 reset、观测转换、Agent masked softmax/抽样、decision 校验、runner、
`env.step` 与统计记账，不计进程启动、预热、确定性序列化和写盘。

| 路径 | 三次 steps/s | 中位数 | 门槛 |
|---|---|---:|---:|
| raw pybind + Agent/runner | 15568 / 15690 / 15921 | 15690 | 通过 |
| 规范 dict + Agent/runner | 8560 / 7923 / 7609 | 7923 | 通过 |
| FlattenWrapper + Agent/runner | 5799 / 5965 / 5910 | 5910 | 通过 |
| TokenWrapper + Agent/runner | 5713 / 5749 / 5777 | 5749 | 通过 |

四条完整路径均高于 2000 steps/s，未出现明确功能热点，因此没有启动性能优化，也
没有用共享可变缓冲破坏 T2 的观测快照独立性。各遭遇分项和原始 wall-clock 见
`docs/week-4-t5-results.md` 与完整 JSON。

## 6. Week 4 双 wrapper 交付（非新增 Gate 项）

- 两条路径只读取同一规范观测白名单；隐藏 seed、RNG、真实抽牌顺序与 `info` 不进入
  模型输入。
- Flatten 输出固定 `float32[182]`；Token 按手牌、敌人、全局、抽牌堆和弃牌堆
  保留实体结构与 mask。本周没有实现可训练投影或 Set Transformer。
- 类别使用明确 one-hot；连续字段不缩放；无效实体行清零。动作仍按原槽位映射，
  wrapper 不重算合法性。
- 手牌/敌人换位、无目标牌、padding 残留、隐藏字段、快照独立和同源追溯均有测试。
- T5 证明两条 wrapper 在同一配置与 Agent 状态下保持相同规范语义、完整 action
  mask、动作、奖励和终局控制流。

## 7. 版本、产物与最终回归

- 基础 commit：`eeb29b8d3df00198c9e52da57c3e14adf39cb109`，与
  `origin/main` 一致。
- T5 正式运行基于未提交代码；可复现补丁为
  `build/week4-t5-worktree.patch`，sha256
  `44985710aefd85390be6d3e82be5a3ece60b0d7391b1b8833abd4be8900c7872`。
- 完整机器结果为 `build/week4-t5-acceptance.json`，sha256
  `0fc4c21b77a73b77b5c07b68777bd8e1c852dfff5fd2f8129f4672f541de85a9`。
- `eval_seeds.json` sha256：
  `38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c`；未修改。
- `build/` 是已忽略的机器产物；仓库保留复跑脚本、测试与结果摘要。

最终回归：

```powershell
python -m pytest -q tests/test_week4_t5.py
# 10 passed in 0.41s

python -m pytest -q
# 138 passed in 0.65s

python -m compileall -q sts tests scripts/run_week4_t5.py
git diff --check
git -C third_party/sts_lightspeed diff --check
git -C third_party/sts_lightspeed apply --reverse --check `
  ../../patches/lightspeed-battle-env.patch
# 以上均通过
```

验收时工作树包含尚未提交的 T5/T6 文件与文档。用户原有的
`杀戮尖塔2 AI方案评估gemini.md` 删除状态不属于本任务，保持未恢复、未暂存、未提交。

## 8. Gate 结论、已知限制与下一步

Gate 1 五项按当前裁定全部通过，不执行 §10 的“砍中等档扩容、锁定最小切片”降级。
Week 5 可以从当前锁定的最小战斗切片继续规划中等档扩容、规则 Agent 与评估入口；
具体任务须先拆分，不能把本 Gate 结论扩张为未规划功能的授权。

已知限制：

- 有限日志存在初始 HP 未对齐、断言失败、范围外跳过和字段/终局未验证；
- 当前只覆盖 A0 Jaw Worm、Cultist、双虱及 Bash/Defend/Strike 最小切片；
- 意图显示数值等观测字段仍保留既有 `[未核实]` 标记；
- 性能只代表记录的本机、构建、单进程及当前随机 Agent，不代表未来含神经网络训练的
  吞吐；
- 压力样本没有触发硬超时，超时分支正确性来自定点测试。

## 9. 学习复盘

工程状态：完成。理解状态：完成（能独立解释）。

用户对本次新例子的回答：

1. `[Defend, Strike]` 换成 `[Strike, Defend]` 后，Strike 从槽位 1 移到槽位 0，
   对应动作起始编号由 3 变 0；玩家 HP 与全局局势总结保持不变。
2. `enemy_mask` 排除补齐的空敌人实体，`action_mask` 直接筛除当前不能执行的动作。
3. Flatten 与 Token 必须输入相同信息；若一条路径多看隐藏 RNG，性能差异就可能来自
   信息优势，不能只归因于 MLP 与 Set Transformer 的架构差异。
4. 正确的 `(敌人 40 HP, Strike, 敌人 34 HP)` 会被共享缓冲污染成
   `(敌人 34 HP, Strike, 敌人 34 HP)`，使模型误以为 Strike 不造成伤害。

评定为“能独立解释”：四个回答均能落到具体动作编号、mask 职责和状态转移，不是复述
抽象定义。结合此前 T1–T5 的信息边界、换位、masked softmax、Agent/环境边界与性能
测量记录，Week 4 理解目标完成。
