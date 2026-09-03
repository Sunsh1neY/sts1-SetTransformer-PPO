# STS RL Agent

Headless《杀戮尖塔 1》Ironclad 战斗模拟器 + A/B 两族模型对照（Set Transformer + PPO vs Decision Transformer）。真实目标：通过工程实践理解 Transformer 原理，游戏是载体。

**唯一执行依据：[`spec-v4.md`](spec-v4.md)**（2026-09-01 定稿）。`spec-v3.md` 及更早版本为冻结愿景，仅供对照。

> 目录名 `sts2` 是 v3 时代（STS2 方案研究）的历史遗留，不改名；实际规格来源是 STS1。

## 当前状态（第 1 周完成，排期见 spec-v4 §9）

- [x] spec-v4 定稿入仓库（覆盖旧的未清理版）
- [x] [docs/decisions.md](docs/decisions.md) —— 13 项裁定 + 推翻条件（D13 反编译查阅政策）+ 未决事项 U1-U6
- [x] [docs/mechanics.md](docs/mechanics.md) —— 结算顺序书面规格 v0.1 + 24 条单测清单 + 游戏本体 RNG 结构核实（§1.1）
- [x] `eval_seeds.json` 生成并提交，sha256 见下方
- [x] `sts_lightspeed` 克隆至 `third_party/`（commit `7476a81`，gitignore + 锁版本）；反编译落位规范见 [reference/README.md](reference/README.md)
- [x] 游戏本体已定位：`E:\SteamLibrary\steamapps\common\SlayTheSpire\desktop-1.0.jar`
- [ ] runlogger mod 未安装 → 创意工坊订阅 + 打几局 Ironclad（第 3 周前，非阻塞）
- [ ] **第 2 周：最小切片模拟器**（`sts/env/`，出口 = 随机策略能打完一场）+ 半天试 build `sts_lightspeed`

## 评估种子

- 评估 seed ∈ [0, 1000)，训练 seed ≥ 100000，`eval_seeds.json` 提交后**不可变**。
- `eval_seeds.json` sha256：`38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c`
- 重新生成（应字节级一致，哈希不变）：`python scripts/make_eval_seeds.py`

## 快速开始

```bash
# 第 2 周 sts/ 包落库后启用
# pip install -e ".[dev]"
# pytest
```

## 约定

- 每个 run 必须落盘：git commit hash / 完整配置 / 随机种子 / `eval_seeds.json` 哈希（spec-v4 §8.1）。
- 每个 run 记录 `eval_seeds.json` 的 sha256，保证跨周结论可比。
- 决策变更先登记 `docs/decisions.md`；结算规格修订先登记 `docs/mechanics.md` 文末变更记录。
