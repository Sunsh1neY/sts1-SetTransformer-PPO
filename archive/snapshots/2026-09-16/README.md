# STS RL Agent

基于《杀戮尖塔 1》Ironclad 的强化学习项目：用无界面的 C++ 战斗环境，沿 A 路径研究 Set Transformer + PPO，并按计划推进 Decision Transformer 对照。真实目标是通过工程实践理解 Transformer 原理，游戏是载体。Python 模拟器保留教学与局部验证用途。

**执行依据：[spec-v6.md](spec-v6.md)**；决策变更见 [决策日志](docs/decisions.md)。学习目标与理解验收见 [学习路径 v2](docs/learning-path-v2.md)。`sts2` 是历史目录名，实际项目规格为 **STS1**；v5 及更早方案只作历史参考。

## 当前状态（2026-09-14）

主分支已整合第一、二幕统一全卡环境与 A 路径模型、Agent、PPO 训练器。后续开发默认沿 A 路径推进；旧 Unified/MLP/Comparison 入口保留为历史回归和对照。

| 范围 | 已完成与边界 |
|---|---|
| Ironclad 卡牌 | 75 类、150 个基础/升级版本 |
| 第一幕 | 20 个常规遭遇 + 2 个事件变体 |
| 第二幕 | 19 个常规遭遇 + 3 个事件战斗 |
| 统一全卡入口 | `sts.env.ironclad.IroncladEnv`；第一、二幕合计 44 个遭遇，另保留第三幕 MAW/TRANSIENT，共 46 个 |
| 环境协议 | A20 单场战斗；逐实体观测、合法动作路由和二次选牌；CARD116 / ENEMY774 |
| 最新本机回归 | A 路径合并后，CPU 1,379 项、独立 C++ 夹具 1 项、CUDA 恢复 1 项通过；CPU 的 CUDA 用例单独执行，无失败、无跳过 |
| 逐卡遭遇诊断 | 6,600 局、零异常；6,397 局自然终止，203 局动作预算截断 |
| 正式训练范围 | 全卡入口仍为 `training_admitted=false`，须显式 `diagnostic=True`；原五遭遇采集器范围未扩大 |

本轮修复了第一幕 Boss 房间分类、六火亡魂产生 Burn+ 的注册缺口，以及构建顺序和换行导致的指纹漂移。详见 [整合报告](docs/act12-main-integration-report.md)及 [逐遭遇/逐版本证据](docs/act12-main-integration-evidence.json)。6,600 局中有 5,934 局实际打出了待测卡版本；这些结果不代表所有卡牌组合与全部机制均已验证。

### 模型与训练进度

- **最小切片 S1–S5 已完成并冻结。** 三初始化训练、开发评估和精确恢复已有证据，见 [S4 报告](docs/ppo-s4-report.md)和 [S5 冻结](docs/ppo-s5-freeze.md)。
- **固定环境 MLP/Set PPO 对照已完成。** 27 种中途卡组、5 个遭遇、两条件；MLP/Set 各两组，每组 70,656 个 transition。四组相对初始策略的开发回报均有改善证据，但 Set−MLP 区间包含 0，不能宣称 Set 架构占优。见 [训练与对照报告](docs/comparison-ppo-report.md)。这组结果不推广到当前全部遭遇。
- **A 路径已合入 main，成为主要开发方向。** 四层 64 维 SAB、4 头、FF128、单 seed PMA，两阶段来源/目标 Pointer 与联合 PPO；使用独立来源组均匀训练池，PPO 对完整 rollout 全局 shuffle。旧训练结果仍保留在归档，检查点不能跨代码/后端指纹直接续训。
- **尚未完成：** 扩大 A 路径训练范围的准入与验证、正式 Gate、完整 RunEnv，以及 Decision Transformer 对照。环境测试通过不等于策略学习或泛化验收通过。

## 当前主线：A 路径

```text
scripts/run-a-path-ppo.py
→ sts.train.apath.APathTrainer
→ sts.env.apath.APathEnv → IroncladEnv / full_card_public → C++ 全卡后端
→ sts.models.apath.encode / batch_samples
→ APathActorCritic：来源分布 × 来源条件目标分布
→ env.step(带快照凭据的动作路由)
→ rollout → GAE → 联合 PPO → 下一次采集
```

交互 Agent 为 `sts.agents.apath.APathAgent`。`scripts/run-unified-ppo.py` 是旧 66 动作路径，不是当前 A 路径入口。

A 路径训练采用独立注册池：39 个训练卡组、33 个来源关联组、两条件、五遭遇，共 390 个初始配置。`APathEnv` 在严格校验注册内容和训练/开发划分后进入正式采集，不借用 `diagnostic=True` 绕过准入。环境支持 44 个一二幕遭遇，不代表训练池自动覆盖全部遭遇。合并边界和验证证据见 [A 路径主线整合报告](docs/a-path-main-integration-report.md)。

构建好后端后，以下命令验证主线的模型与训练恢复接口，不启动历史四小时运行：

```powershell
python -m pytest -q tests/test_apath.py tests/test_apath_training.py -k "not cuda"
```

受限 CUDA 训练脚本为 `scripts/run-a-path-ppo.py`，参数见 `--help`；运行前须明确本次预算、输出目录及训练范围。历史 I4 的训练预算不随本次合并重新启动。

## 快速开始：统一全卡环境

当前构建流程以 **Windows + MSYS2 mingw64 + Python** 为已验证环境；本机使用 Python 3.13。构建与运行必须使用同一个 Python 解释器。

先在 MSYS2 安装工具链（默认位置 `C:/msys64/mingw64/bin`）：

```bash
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja
```

然后在项目根目录的 PowerShell 中执行：

```powershell
python -m pip install -e ".[dev]"
./scripts/build-enemy-potion.ps1 -Python python -Jobs 1
```

统一构建入口按 [版本锁](scripts/lightspeed-lock.json) 准备后端，应用基础及敌人集成补丁、生成契约并核对运行指纹。只有拉取 Python 源码或执行基础构建脚本，不能保证获得当前全卡后端。遇到已有源码冲突时脚本会停止并保留现场。

以下示例创建一个第一幕 A20 战斗，并使用合法路由完成一次决策；同一路由接口也用于二次选牌：

```python
from sts.env.ironclad import IroncladEnv
from sts.env.entities import encode_observation

scene = dict(
    entry_timing="pre_combat_initialization",
    initialization_phase="before_destination_room_entry",
    act=1, floor=8, character="IRONCLAD", ascension=20,
    player=dict(hp=80, max_hp=80, gold=100),
    deck=["Strike_R"] * 3 + ["Defend_R"] * 3
         + ["Bash", "Headbutt", "True Grit+1", "Seeing Red"],
    relics=[], potions=[None, None],
    encounter="CULTIST", burning_elite=False,
)
env = IroncladEnv(128)
observation = env.reset(scene, seed=100000, diagnostic=True)
sample = encode_observation(observation)
action = next(route for route, candidate in zip(sample.routes, sample.candidates)
              if candidate.legal)
observation, reward, terminated, truncated, info = env.step(action)
```

共享实体与动作接口见 [统一实体接口](docs/unified-entity-interface.md)。全卡场景准入以 [环境契约](sts/env/ironclad-expansion-contract.json) 和 [卡牌注册表](sts/env/ironclad-registry.json) 为准；`diagnostic=True` 不授予正式训练准入。

### 验证

构建完成并准备好本地测试资料后，分别运行 CPU 回归和直接编译的 C++ 状态夹具：

```powershell
python -m pytest -q --ignore=tests/test_enemy_status_export.py -k "not cuda"
python -m pytest -q tests/test_enemy_status_export.py
```

全量测试部分依赖被 Git 忽略的本地资料；新 clone 不自带历史实验、原始语料或仲裁资料。缺少资料、后端或指纹不一致需要补齐对应依赖，不能把失败或跳过当作验收通过。尚未准备后端时，可先运行教学层测试：

```powershell
python -m pytest tests/test_ordering.py tests/test_rng.py tests/test_replay.py tests/test_random_agent.py
```

重新执行第一、二幕逐卡诊断可使用以下命令；输出路径必须尚不存在：

```powershell
python scripts/diagnose-enemy-full-card.py --act12 --output reference/act12-local-diagnostic.json
```

## 保留的历史入口

这些入口各有版本和证据范围，旧检查点须配合原源码、依赖和运行指纹使用。

| 入口或阶段 | 用途与文档 |
|---|---|
| `LightspeedBattleEnv`、`FlattenWrapper`、`TokenWrapper` | A0 Jaw Worm、Cultist、双虱的冻结最小切片；31 动作协议，见 [观测契约](docs/observation-contract.md) |
| `PublicBattleEnv`、`RuleAgent` | 公开派生场景与规则基线，见 [公开环境实施报告](docs/public-battle-implementation.md) |
| 固定五遭遇 MLP/Set 对照 | 相同信息与 66 动作的历史对照，见 [M3 训练范围](docs/comparison-m3-training.md) |
| 统一实体扩展 | 全卡环境的实体表示和动作路由，见 [实体工程报告](docs/unified-entity-report.md) |

早期报告中的“下一步 S4/S5”“Set 尚未实现”以及旧测试数量属于当时快照；当前状态以上方进度为准。

## 主目录与归档

桌面 STS 项目已整理为一个 `sts2` 主目录，本地仅登记 `main` 工作树和分支。A 路径代码现已合入 main；辅助目录、历史训练检查点、未提交后端修改及旧分支历史仍完整保留在本机：

```text
reference/desktop-repo-archive-20260914/
├── all-refs.bundle          # 清理前的完整 Git 历史
├── manifest.json            # 原路径、提交和逐文件哈希
├── original-directories/    # 六个原目录，含旧实验与后端
└── *.zip                   # 已校验的目录压缩副本
```

详见 [清理与恢复说明](docs/desktop-repo-cleanup-2026-09-14.md)。归档属于本地文件快照，旧工作树指针和构建缓存不能直接当作当前可运行环境；继续旧实验前须按说明恢复并验证。

`reference/`、`runs/`、`third_party/` 及检查点等被 Git 忽略，**普通 push 不会上传这些本地产物**。备份实验时需要额外保存它们。

## 固定约定

- 评估 seed ∈ [0, 1000)，训练 seed ≥ 100000；`eval_seeds.json` 提交后不可变，SHA-256 为 `38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c`。seed 不进入模型状态。
- `battle_reward_v1`：非终局 0，首次胜利 `1 + 0.5 * 退出HP / 最大HP`，失败 0；γ=1、β=0。未来完整 run 使用独立奖励版本，普通战斗胜利不能记作全局通关。
- 真终止不自举；外部截断使用 reset 前最终观测自举，GAE 不跨 reset。容量或诊断预算截断不能伪造成失败 0。
- 合法动作由环境给出，掩码在 softmax 前应用；卡牌槽位仅用于动作对应，不作为卡牌语义特征。观测只使用允许公开的信息。
- 每个训练 run 保存源码及后端指纹、配置、版本、seed、曲线与检查点；PPO 还须保存优化器、计数、RNG 和活动环境恢复依据，并验证续训一致性。
- 规格变更先登记 [决策日志](docs/decisions.md)，机制结算以 [机制规格](docs/mechanics.md) 为准。历史测试、诊断和学习结果分别报告，不互相替代。
