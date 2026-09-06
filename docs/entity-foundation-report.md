# D24 逐牌实体基础验收报告

验收日期：2026-09-06。依据：`spec-v4.md` §4.2、§5.1、§9，
`docs/decisions.md` D24，以及 `W4-sts-entity-foundation-agent-plan.md` P4–P5。

结论：**D24 逐牌实体版工程验收通过，可以回到 Week 5–6 主线。** 本报告是旧计数版
Gate 1 之后的补充迁移验收，不把旧结果冒充新输入结果，也不新增一个规格外 Gate。

## 1. 实际范围

- 正式 C++ 适配层与 Python 规范观测导出手牌、抽牌堆、弃牌堆、消耗堆四区逐牌记录。
- `CardRegistry` 提供稳定项目 ID、后端 ID、名称和目标类型；PAD 与有效类别分离。
- FlattenWrapper 与 TokenWrapper 共用同一 V2 数据准备路径，类别、数值、known、valid
  和动作 mask 分开传递；wrapper 不包含可训练参数。
- 正式任务仍只有 A0 Jaw Worm、Cultist、双虱和 Bash、Defend、Strike。合成第四类卡
  只用于证明数据协议可扩展，不进入正式 reset，也不声称支持新卡机制。

## 2. P4：动作闭环与第四类卡探针

真实双 wrapper 闭环继续覆盖三种遭遇：Agent 在掩码后分布中抽样并返回整数动作，
runner 原样转交；手牌槽位按 `slot * 3 + target` 路由，无目标牌只用列 0，结束回合
保持动作 30，终局后不再调用 Agent。

新增的第四类合成卡探针建立测试专用 registry version 2，登记
`registry_id=4`、`backend_card_id=999999`、`target_kind=ENEMY`。同一类别分别放入手牌、
抽牌堆、弃牌堆和消耗堆，仅修改测试注册条目与观测数据；两条 wrapper 无按牌名分支即
可处理，并能逐字段恢复为相同信息。未知未登记 ID 仍在写入张量前报错。

边界例：三个非手牌区域合计超过 `pile_capacity=10` 时明确抛错，不静默截断。这个
检查证明数据丢失会被阻止，不证明容量 10 足以容纳 Week 5 的中等档牌组；扩容时须
显式调整 schema 与兼容性。

专项命令与结果：

```powershell
python -m pytest -q tests/test_wrappers.py tests/test_masked_policy.py `
  tests/test_week4_t5.py
# 48 passed in 0.54s
```

## 3. P5：确定性、稳定性、奖励与性能

正式复跑命令：

```powershell
python scripts/run_week4_t5.py --episodes 10000 --repeats 3 `
  --warmup-episodes 100 --determinism-episodes 60 `
  --output build/entity-foundation-acceptance.json
```

每条路径每轮均为 10000 场、184117 步、8711 胜 / 1289 负；三轮的异常、非法动作、
硬超时和奖励契约失败均为 0。四路径使用相同环境 seed 与 Agent seed，不能用某条路径
更幸运解释差异。60 场分层确定性重放覆盖三遭遇各 20 场，路径内失败 0，跨路径规范
语义失败 0。

单核完整路径性能中位数：

| 路径 | steps/s | 2000 门槛 |
|---|---:|---:|
| raw pybind | 14702 | 通过 |
| 规范 dict | 5882 | 通过 |
| FlattenWrapper | 3841 | 通过 |
| TokenWrapper | 3790 | 通过 |

秒表包含 reset、观测转换、Agent masked softmax/抽样、decision 校验、runner、step 与
记账；不含进程启动、预热、确定性序列化和写盘。实体记录校验与整理使包装路径慢于
旧计数版，但最慢路径仍为门槛的约 1.89 倍，未触发性能降级。

## 4. 版本与完整回归

- 基础提交：`eeb29b8d3df00198c9e52da57c3e14adf39cb109`；验收在未提交工作树执行。
- `eval_seeds.json` sha256：
  `38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c`，未修改。
- 适配补丁 sha256：
  `619d7d1c00ec4fd9c1e1499d9a3b37d84d8b98f01cc932d68f61be07ce2e7a6e`。
- 本机构建扩展 sha256：
  `e55552b105755889b1130967420f37591cc6e74433fcac370d8218ff7bda4ec9`。
- 机器结果：`build/entity-foundation-acceptance.json`，sha256
  `e2434a977013d965a47908f29d76293d01d4dcc8ddbc62f23c22bce85624b38a`；`build/`
  已忽略，不进入 Git。

```powershell
python -m pytest -q tests/test_ordering.py tests/test_cpp_env.py `
  tests/test_wrappers.py tests/test_masked_policy.py tests/test_week4_t5.py
# 98 passed in 0.61s

python -m pytest -q
# 146 passed in 0.74s

python -m compileall -q sts tests scripts/run_week4_t5.py
git diff --check
# 通过
```

## 5. 能证明什么、不能证明什么

本次证明逐牌实体协议在当前正式 C++ 切片中保持信息、动作与奖励闭环，能拒绝未知类别
和超容量，并在当前机器上达到稳定性、确定性和吞吐门槛。第四类探针证明“现有字段足以
描述的新类别无需修改整理层”，不证明模型已经学会该卡，也不证明后端实现了该卡效果。

本次仍不证明正版 STS1 全机制等价；旧 Gate 记录中的日志差异、字段未验证与
determinismfix 未销账继续有效。中等档扩容必须先核实卡表来源，再逐项扩环境机制、
注册数据、可见字段、容量和回归，不能因本报告通过而一次性开放未实现内容。
