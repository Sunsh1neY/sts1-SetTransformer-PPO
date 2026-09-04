# STS RL Agent

Headless《杀戮尖塔 1》Ironclad 战斗模拟器 + A/B 两族模型对照（Set Transformer + PPO vs Decision Transformer）。真实目标：通过工程实践理解 Transformer 原理，游戏是载体。

**唯一执行依据：[`spec-v4.md`](spec-v4.md)**（2026-09-01 定稿）。`spec-v3.md` 及更早版本为冻结愿景，仅供对照。

> 目录名 `sts2` 是 v3 时代（STS2 方案研究）的历史遗留，不改名；实际规格来源是 STS1。

## 当前状态（第 2 周完成主线，排期见 spec-v4 §9）

- [x] spec-v4 定稿入仓库（覆盖旧的未清理版）
- [x] [docs/decisions.md](docs/decisions.md) —— 15 项裁定 + 推翻条件 + 未决事项（U4/U6/U7 已销账）
- [x] [docs/mechanics.md](docs/mechanics.md) —— 结算顺序书面规格 v0.1 + 24 条单测清单 + 游戏本体 RNG 结构核实（§1.1）
- [x] `eval_seeds.json` 生成并提交，sha256 见下方
- [x] `sts_lightspeed` 克隆至 `third_party/`（commit `7476a81`，gitignore + 锁版本）；反编译落位规范见 [reference/README.md](reference/README.md)
- [x] 游戏本体已定位：`E:\SteamLibrary\steamapps\common\SlayTheSpire\desktop-1.0.jar`
- [ ] runlogger mod 未安装 → 创意工坊订阅 + 打几局 Ironclad（第 3 周前，非阻塞）
- [x] `sts/env/rng.py`：java.util.Random 逐位复刻 + 11 项测试（D14）
- [x] **最小切片模拟器**：state / cards / effects / enemies / combat / actions 全部落库；`tests/test_ordering.py` T01-T24 跑绿（T23 规格性 skip）
- [x] **周 2 出口达成**：随机策略三种遭遇 60 局全部自然终局、同 seed 轨迹逐步一致（`tests/test_random_agent.py`）；随机胜率参考：Jaw Worm 18/20、Cultist 14/20、Louses 20/20（非门槛，供第 5-6 周规则基线对照）
- [x] **U4 build 成功**：MSYS2 mingw64 gcc 16.2 + CMake 4.4 + Ninja 编过 `test` 目标，3 局 playout 冒烟通过（2.5ms）；Python 绑定已修复——pybind11 升级 v2.13.6（D15），`import slaythespire` 验证通过

## 评估种子

- 评估 seed ∈ [0, 1000)，训练 seed ≥ 100000，`eval_seeds.json` 提交后**不可变**。
- `eval_seeds.json` sha256：`38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c`
- 重新生成（应字节级一致，哈希不变）：`python scripts/make_eval_seeds.py`

## 快速开始

```bash
pip install -e ".[dev]"
pytest   # 37 passed, 1 skipped（T23 规格性 skip）
```

`sts_lightspeed` 构建复现（Windows + MSYS2，见 docs/decisions.md D15）：

```bash
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja
cd third_party/sts_lightspeed && git submodule update --init --recursive
git -C pybind11 fetch --tags && git -C pybind11 checkout v2.13.6   # 绑定需 2.13+（D15）
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_CXX_COMPILER_LAUNCHER="cmd;/c;<repo>/scripts/lightspeed-gxx-wrap.bat"
cmake --build build   # 含 test.exe 与 slaythespire 绑定模块
cp /c/msys64/mingw64/bin/{libstdc++-6,libgcc_s_seh-1,libwinpthread-1}.dll build/
./build/test.exe simple_agent_mt 1 1 3   # 冒烟：3 局 playout
python -c "import sys; sys.path.insert(0, 'build'); import slaythespire; print('ok')"   # 绑定冒烟
```

## 约定

- 每个 run 必须落盘：git commit hash / 完整配置 / 随机种子 / `eval_seeds.json` 哈希（spec-v4 §8.1）。
- 每个 run 记录 `eval_seeds.json` 的 sha256，保证跨周结论可比。
- 决策变更先登记 `docs/decisions.md`；结算规格修订先登记 `docs/mechanics.md` 文末变更记录。
