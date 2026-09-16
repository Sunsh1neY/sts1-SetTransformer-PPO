> **Historical navigation notice (2026-09-16):** This is a dated phase record or instruction set, not a current work order. Use the [documentation map](README.md), [spec-v6](../spec-v6.md), and registered amendments for current work. Original commands, paths, budgets and evidence below retain their historical scope.

# 敌人扩展共同基线

日期：2026-09-13。负责人：R。状态：共同基线准备中，字段审批待用户裁决，未启动其它 agent，未运行正式训练。

本文记录分发前已经核对的源代码、后端、补丁、契约、冻结文件和本地验证结果。`sts2` 主工作树的未提交成果属于并行 M3 工作，按原状态保留，不能被本任务的基线提交吸收。

## 1. 源代码基线与隔离

| 项目 | 实际值 |
|---|---|
| 敌人扩展目录 | `C:/Users/19091/Desktop/sts2-enemy-potion` |
| 分支 | `codex/enemy-potion-expansion` |
| 敌人扩展成果源提交 | `8f3d3c74885fd4766c1ef29ad9b8617af3a9e08a` |
| 共同基线提交 | `29013d334c8ad6adeceea00dc29d442067bb982b`；路径状态更新后四个 worker 分支快进到本文件所在的最终交接提交 |
| 分发原则 | A/B/C/D 从同一共同基线创建，worker 只写自己的 worktree；当前四个目录均已创建 |
| 全卡参考目录 | `C:/Users/19091/Desktop/sts2-full-card`，只读 |
| 全卡参考提交 | `2325d550bee2e3ffb28474af8652e7c852b756b4` |
| 全卡共享契约 | `unified-entity-interface-v4`，SHA256 `12cd3f67b7563699dba801079b21a2729799349f1043210330ffbec99d11e843` |
| 全卡实体编码源码 | `sts/env/entities.py`，SHA256 `39b02cbe5bed2f8820632bd10295d01c592cacfff8d604944ca5373293723597` |

分发目标已经确认不存在，且本地分支名不存在：

| 组 | worktree | 分支 | 后端源码 | 后端构建目录 |
|---|---|---|---|---|
| A | `C:/Users/19091/Desktop/sts2-enemy-a` | `codex/enemy-a` | `C:/Users/19091/Desktop/sts2-enemy-a/third_party/sts_lightspeed` | `C:/Users/19091/Desktop/sts2-enemy-a/third_party/sts_lightspeed/build` |
| B | `C:/Users/19091/Desktop/sts2-enemy-b` | `codex/enemy-b` | `C:/Users/19091/Desktop/sts2-enemy-b/third_party/sts_lightspeed` | `C:/Users/19091/Desktop/sts2-enemy-b/third_party/sts_lightspeed/build` |
| C | `C:/Users/19091/Desktop/sts2-enemy-c` | `codex/enemy-c` | `C:/Users/19091/Desktop/sts2-enemy-c/third_party/sts_lightspeed` | `C:/Users/19091/Desktop/sts2-enemy-c/third_party/sts_lightspeed/build` |
| D | `C:/Users/19091/Desktop/sts2-enemy-d` | `codex/enemy-d` | `C:/Users/19091/Desktop/sts2-enemy-d/third_party/sts_lightspeed` | `C:/Users/19091/Desktop/sts2-enemy-d/third_party/sts_lightspeed/build` |

四个目录在记录时均不存在；创建它们不会覆盖现有目录。每个后端副本都必须由锁定后端和两份补丁重新生成，不能复制或共享当前 `third_party` 下的可写构建树。

已创建结果：四个 worktree 的顶层状态均干净，且均从共同基线提交创建；四个后端 build 目录均已建立但尚未编译，避免在未分配任务前重复占用资源。后端源码与生成头的 SHA、锁定子模块和路径在本文件第 3 节及最终状态表中复核。

## 2. 未提交成果的保留记录

### 2.1 主工作树 `C:/Users/19091/Desktop/sts2`

盘点时 HEAD 为 `0d68033d2b2fb7a042d33343b863af7c3e818967`，分支为 `main`，状态为 `## main...origin/main`。以下修改和未跟踪文件不属于本任务基线，未被复制、提交或重置。

已修改文件：`.gitignore`、`AGENTS.md`、`docs/decisions.md`、`docs/mlp-set-comparison-boundary.md`、`docs/real-deck-training-plan.md`、`docs/week-5-6-plan.md`、`spec-v6.md`。

未跟踪文件及工作副本 SHA256：

| 路径 | SHA256 |
|---|---|
| `docs/comparison-gpu-runtime.md` | `160409b1f6b57fed4da6c6784806b403f0322067a9c552646e0706fc528185ca` |
| `docs/comparison-m3-training.md` | `3cd300f3f944bf1bd488b5e6ff8b825f72da1aa5246b01acce6c6f8bdd06f7c6` |
| `docs/comparison-ppo-report.md` | `0ef7c4f52ede1f6af18dab4aa608c8c1207fb705da4a1e0f54a78eecd6129054` |
| `docs/ironclad-full-expansion-plan.md` | `ab8f63480146591e706bbe3b2be537ec76de5177a780202cb60ac3a7b85d5f66` |
| `docs/ironclad-input-audit.md` | `767c65c838f5b3373a3ad207154a187d42af38454c3ff099bc1c50184cced8a0` |
| `docs/ironclad-input-requirements.md` | `5a7c2dedee802bb08d6baf6e132c77ff4d3dc46af321d51ecd208b2cb40c57e8` |
| `docs/unified-set-training.md` | `cae4013bcd96fd1bd40803648a8344afa376702ea8f1254a15b4dae692c86519` |
| `scripts/diagnose-comparison-capacity.py` | `797d5dafa5c1c1cb37cd1a3f0bd8c5f7c44d5b10e380250d67bf8dba53ce1ac9` |
| `scripts/prepare-comparison-contract.py` | `ee32b8c1516931f1738e0908eece79dd1ec84461c908209c3fe1d3a900dc091d` |
| `scripts/report-comparison-ppo.py` | `3b9979f3dcd586f26845a9b6737636d90c25c6d1ed1e4064beb5fc049bc1ca9c` |
| `scripts/run-comparison-ppo.py` | `b0be930504b3132a0327c4d6b7a91b24955bcd9843e13def827b91beeb151439` |
| `scripts/run-unified-ppo.py` | `3ebc82176245b65106cecd2ef4f5037b72839702dd4a2d1bbeef3f093c5b5c2b` |
| `scripts/show-post-training-episode.py` | `86d7782ee498eb9e3d89dc9a63ae40a51485804930b19d62a9831c639ae0e844` |
| `sts/env/comparison-contract.json` | `6d0dcf25ba2a603c4edc7c32c28484eb419255a7cf79bb7bae10245aa1cf6497` |
| `sts/env/comparison.py` | `452cfd4972e73a4e39718ff713fe65b4f8f0615025a5d452a7133374e4f2f010` |
| `sts/env/unified.py` | `e7ad0bc45e04ac0782136112b9933e5f39d089add6186a39da3ecdaee7eb9ec4` |
| `sts/models/comparison.py` | `7184acd18ae807bceb7e59ee8ec5b48a437e738c8c0d6d997468cbd05e0962de` |
| `sts/models/unified.py` | `333ce66c094b5e38e1aee667328251359e4248cd2495da6c258e4bc30b153e5a` |
| `sts/models/unified_fields.py` | `112db0a74ea64d7635b586bc3db76ff49e470d55a240bfe0f662cefc1caad76a` |
| `sts/train/comparison.py` | `951f49137f1e7b62b8723b6204097ee768f56669525f3bfb923882d7286f0b2c` |
| `sts/train/unified.py` | `e3d8709b37273bb3195edf46a1961e155b17ba35c1f839c22f5a39a7b36d07bb` |
| `tests/test_comparison_training.py` | `2d00a51d5f8c2b6d8f28f025b64de3924116c1bc1e4dfbc7611bee043b2f4856` |
| `tests/test_unified_training.py` | `ec95b2db35f9ea03300ba3e914f123e05e6e8f9a7f86dcec979c2204de8ce208` |

主工作树的未跟踪文件数量、路径和哈希已在基线准备时核对；本任务不使用其内容，也不以本任务的提交替代主工作树的保存动作。

### 2.2 敌人交付工作树

交付目录在成果源提交之后原本干净。刷新全卡只读审计后只产生一项可归属于本任务的文档修改：`docs/enemy-potion-shared-handoff.json`。该刷新把旧的 `unified-entity-interface-v1` / 旧哈希更新为当前全卡提交的 v4 / 当前哈希，属于基线整理，已列入本次基线提交。

交付目录下的 `third_party/sts_lightspeed` 是被忽略的独立后端现场，不能由 Git 顶层提交解释。它当前包含：

- 后端锁定 HEAD `7476a81954020087da31d41d16fddf475746ec2` 上的基础适配和敌人增量源码改动；
- `pybind11` 实际指针 `a2e59f0e7065404b44dfe92a28aca47ba1378dc4`；
- 生成头 `bindings/enemy-potion-config.h`，SHA256 `11c3f8cc7641eef2320130a5f8cdd5fe4a2088f64eab916f4ba4ca03d7980bd1`；
- 原有 `build`、`build-before-desktop-move` 及诊断二进制。

这些后端源文件和构建产物均不作为 worker 共享目录。worker 必须在自己的目录中重新应用补丁并生成配置头。

## 3. 后端、补丁和构建锁定

| 项目 | SHA / 路径 | 核验结果 |
|---|---|---|
| `sts_lightspeed` 后端 | `7476a81954020087da31d41d16fddf475746ec2d` | 与 `scripts/lightspeed-lock.json` 一致 |
| `json` 子模块 | `0b345b20c888f7dc8888485768e4bf9a6be29de0` | 与锁文件一致 |
| `pybind11` 子模块 | `a2e59f0e7065404b44dfe92a28aca47ba1378dc4` | CPython 3.13 构建锁定 |
| 基础适配补丁 | `patches/lightspeed-battle-env.patch`，SHA256 `fe8168a3cbfa5595fefa7e9bf205ea9db0dc017096ac4809120feb8d8896c9aa` | 在干净后端正向 check/apply 退出码均为 0 |
| 敌人增量补丁 | `patches/lightspeed-enemy-potion.patch`，SHA256 `366510ec096ab323e95a76b97dea73adb420573049c4f8e4cfdbb814a0cde65a` | 在基础补丁后正向 check/apply 退出码均为 0 |
| 反向复现 | 同一临时副本先反向增量、再反向基础补丁 | 两次 check/apply 退出码均为 0 |

当前交付后端上直接反向基础补丁失败是预期的重叠上下文现象：增量补丁尚未反向时仍修改 CMake 和绑定注册处，不能把这个直接检查当作基础补丁不可复现。独立副本按正确逆序已通过。

干净重放目录为 `C:/Users/19091/Desktop/sts2-enemy-patch-repro`，正向和逆向补丁复现均未修改交付后端。干净构建基线目录为：

- 后端源码：`C:/Users/19091/Desktop/sts2-enemy-baseline-backend`；
- 构建目录：`C:/Users/19091/Desktop/sts2-enemy-baseline-build`；
- 编译器：`C:/msys64/mingw64/bin/g++.exe`，GCC 16.2.0；
- CMake：4.4.2；Ninja；Python：`C:/Users/19091/AppData/Local/Programs/Python/Python313/python.exe`，Python 3.13.2；
- 生成模块：`slaythespire.cp313-win_amd64.pyd`，SHA256 `b3b959852d70cb065fdb3dbe7f8c1387f943c2cd357fa66b02a48a18737c3085`；
- 独立模块加载检查：通过，`EnemyPotionBattleEnv` 存在且导出的契约哈希等于 Python 契约哈希。

干净构建的 CMake 配置必须先设置 `PATH=C:/msys64/mingw64/bin;现有PATH`，并使用仓库内 `scripts/lightspeed-gxx-wrap.bat` 作为 launcher。上游锁定 `.gitmodules` 的 pybind11 URL 是迁移后不可直接使用的相对本机路径；复现时在独立副本的 Git 配置中把该 URL 指向本机锁定子模块，不能修改交付分支的 `.gitmodules`。

## 4. 契约与冻结文件哈希

| 文件 | SHA256 |
|---|---|
| `sts/env/enemy-potion-contract.json` | `b61dc3c38501f7a8664c2f148de67f3949140b90acb64fd32714dd385d7d271d` |
| `sts/env/enemy-potion-coverage.json` | `e6c59d55463bf07f3a1b492e84501a8c3535964a900cdcd8dd52d203a8a3907e` |
| `docs/enemy-intent-vocabulary.json` | `bb69f3d80dd2ee8b6433ad1d92acb14295a8c34df85e9833ea35c957a830b401` |
| `docs/enemy-intent-example-v3.json` | `4abcc622f8a0d9239b03befc9a47a61f3bbcf68ba8ce108b70e07ed1b1c16d7d` |
| `docs/enemy-potion-entity-interface.md` | `8286b15df5d1a6256f6cb9fbe31497c5c62cf4431f0e0ec920a873e07b90e3c4` |
| `docs/enemy-potion-entity-example.json` | `50d556db32e09c2754ea552b3317727324782328c82f21bcc29d295671ceb2bf` |
| `docs/act23-enemy-audit.json` | `fa3756d9d07c3033504ff0d9a15ff425b1ea10acf781cebf1bc3cf81d78531e2` |
| `docs/act23-enemy-evidence.json` | `29c9edee1b2c0313eebb0c545874204c9b0a8d599603a0d0571ad65957bdc377` |
| `docs/act23-enemy-review.md` | `89076336c762a7f216e737df7be36e9ba2b59698815b91870055508e80b7f32` |
| `docs/enemy-potion-expansion-progress.md` | `1adcac48cf25b820eeddaa36c440678a560269484d68e37cee885ec4b22327d1` |
| `docs/enemy-potion-shared-handoff.json` | `a01d65c9ce8ecfd65f1581fa157d4e3fc39381adbd843d45c4226a4860482d11` |

交付前需再次运行哈希核对，避免复制排版错误。

原冻结文件实际哈希与 `docs/enemy-potion-frozen-hashes.json` 完全一致：

| 冻结文件 | SHA256 |
|---|---|
| `eval_seeds.json` | `38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c` |
| `patches/lightspeed-battle-env.patch` | `fe8168a3cbfa5595fefa7e9bf205ea9db0dc017096ac4809120feb8d8896c9aa` |
| `sts/env/public-battle-contract.json` | `cc29dad191bd560d6b4f03d048387ba2a1a41d19bb08b1ea3891dcf618e4bea5` |
| `sts/env/real-deck-batch.json` | `59c837a108ae7275c61a187dd3bc19e190953a15ac8fe2d7f5bbb37c5fc0acfe` |

## 5. 当前验证结果

以下是本次基线整理实际执行的结果，不继承上一轮报告数字：

| 检查 | 实际结果 | 边界 |
|---|---|---|
| Python 定向回归 | `317 passed in 15.60s` | 敌人扩展、实体、旧 public/minimal 和 C++ 适配器；不是全仓回归 |
| `scripts/check-spec-v6.py` | `PASS`，spec-v6 757 行，入口文档 11 | 规格静态检查 |
| `scripts/check-enemy-potion-capacity.ps1` | `4 capacity checks passed` | 既有队列写入保护；不代表极端容量证明 |
| 13 个已准入遭遇诊断 | 312 局，36 胜、276 败、0 截断、0 异常、0 未完成，5726 transitions | 合成卡组、空药水、开发诊断；不代表真实分布、PPO 或统一模型准入 |
| 诊断原始文件 | `reference/act23-enemy-diagnostic.json`，SHA256 `ef0b0ee7326922c197aab12cca0639014840632539452395e3f3711f0b30a899` | 被忽略的本地证据 |
| C++ 模块导入 | 通过；现有交付 build 导出的契约哈希与 Python 哈希均为 `b61dc3c38501f7a8664c2f148de67f3949140b90acb64fd32714dd385d7d271d` | 现有脏 build 的加载检查；干净 build 另有独立记录 |
| 22 个待审遭遇 | 当前未进入契约白名单；现有测试只验证 reset 被拒绝 | 没有机制通过数字，不能写成已实现 |

复现命令：

```powershell
python -X utf8 -m pytest -q tests/test_act23_enemies.py tests/test_enemy_potion.py tests/test_enemy_potion_entities.py tests/test_public_consumables.py tests/test_public_encounters.py tests/test_public_battle.py tests/test_cpp_env.py tests/test_lightspeed_adapter.py
python -X utf8 scripts/check-spec-v6.py
.\scripts\check-enemy-potion-capacity.ps1
python -X utf8 scripts/diagnose-act23-enemies.py
python -X utf8 scripts/audit-enemy-potion-shared.py --shared-root C:/Users/19091/Desktop/sts2-full-card
```

本次没有运行正式训练、没有修改 `eval_seeds.json`、没有向全卡原工作树写入、没有 push、没有合并主分支。字段审批前不改变生产 schema、状态词表、region 词表、候选协议或统一模型输入。

## 6. 分发前后检查点

1. 共同基线提交后，四个 worktree 必须显示相同的源码基线 SHA。
2. 四个后端源码目录必须各自显示锁定后端 HEAD、独立子模块和独立 build 路径；不允许路径指向 `sts2-enemy-potion` 或另一个 worker。
3. worker 的增量补丁必须注明相对共同基线和后端锁定 SHA；同一共享文件的改动由 R 串行合入。
4. 新增或修改字段、状态取值、region 取值、字段更新时点、phase 语义和候选协议在用户批准前只能存在于提案或诊断夹具中。
5. 任何遭遇只有在机制、观测、合法动作、终局、奖励、回归、独立构建和补丁复现全部通过后，才能把 `docs/act23-enemy-audit.json` 对应条目改为准入；本批未修改现有 33 项状态。
