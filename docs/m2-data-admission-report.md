# M2 派生初态数据准入与完整场景清单

日期：2026-09-12。依据已登记的 `public-derived-standard-v1`，已实现数据准入维度与完整实体筛选；后端行为、容量和正式训练/评估仍分别待验收。

## 结果

固定203文件、157个run组、1282个第一幕战斗行保持不变；257场规则可构造候选全部保留，来源策略维度记为 `admitted_backend_pending`，历史规则等价仍 `unverified`。原 `reconstruction_status=rule_constructible_source_unverified` 保留，未把它覆写成精确复盘。

完整初态内容以M1的35类牌、额外必需AscendersBane、8项RESET遗物及15种直接药水筛选，得到99场、75个run组。其余158场连同完整candidate及拒绝原因保留，不删牌、不删遗物、不屏蔽药水再当作原场景。

| 清单指标 | 结果 |
|---|---:|
| 完整候选保留 | 257 |
| 内容实施候选 | 99 |
| 独立run组 | 75 |
| train / dev / reserved-eval场景 | 73 / 24 / 2 |
| 初态牌类别 | 22，包含AscendersBane |
| 普通遭遇类别 | 6 |
| 最大初始牌组 | 14 |
| 本清单声明正式可运行数量 | 0 |

六种遭遇为Cultist27、Jaw Worm16、2 Louse32、Small Slimes22、2 Fungi Beasts1、Looter1。这里的数量不足以宣称M3的30–40类牌或M4的约10普通遭遇加3精英已完成；保留评估只有2场，更不能称充分泛化评估。

## 实现与信息边界

- `scripts/audit-public-corpus.py` 升级审计schema为v2；新增来源策略、派生数据准入、历史等价未知、后端pending四个独立字段。
- `basemod:card_modifiers` 缺失与全null只保留不同证据状态。任何非空修饰或非列表结构导致整个关联run组拒绝，代表文件没有修饰也不能绕过其他别名的拒绝。现有157个独立内容中111缺失、46全null，因此本轮未因此减少257场。
- `scripts/build-public-scene-manifest.py` 先校验corpus文件SHA、index与corpus内容一致、审计脚本SHA、固定归档SHA。manifest保留输入SHA、builder SHA、候选内容SHA及自身规范化payload SHA。自身SHA计算排除唯一的 `manifest_payload_sha256` 字段，避免自引用。
- 每个scene保留scene_id、group_id、research_split、source路径/哈希/build/seed、完整candidate、source_group别名与关联标识。source seed只作来源与分组元数据，`source_seed_policy` 明确 `never-model-input`；本工具不生成模型输入。
- `content_admission_status=accepted` 仅表示完整初态在本批实施候选内容内；`content_blockers` 写出整体拒绝原因。兼容保留更明确的 `implementation_batch_status` 与对应blockers。`formal_training_ready=false`、`formal_evaluation_ready=false` 不因内容准入改变。
- `entity_closure` 记录初态卡类与可达生成卡类：Wild Strike/Power Through→Wound、Reckless Charge→Dazed、Immolate→Burn，以及有关史莱姆遭遇→Slimed、三哨卫→Dazed。具体实例、增殖次数、怪物分裂及全过程容量仍待后端验收，不将类别并集当作容量证明。

生成类别映射复核了锁定后端 `MonsterGroup.cpp` 的遭遇生成和 `MonsterSpecific.cpp` 的临时牌路径。Lots of Slimes仅小型史莱姆，Gremlin Gang不因此被误记为Dazed生成；Exordium Thugs的弱野生池确实含中型史莱姆。卡类与永久状态支持依据仍沿用M1及既有定点证据，不新增历史版本等价主张。

## 实际验证

执行离线corpus重建与manifest生成成功。数据侧专测 `tests/test_public_corpus.py`、`tests/test_public_scene_manifest.py` 共41项通过，无失败；未由本任务运行全仓回归，交主审统一执行。

新增反例覆盖：修饰非空/格式异常整场及整组拒绝、关联顺序不改变group/split、未知实体和二次选择药水整体延期、True Grit升级不准入、scene不重复/同组split一致、完整candidate不被裁剪、生成类别、候选和payload哈希、自身输入文件与内容篡改拒绝。

本任务没有修改规范/正式runtime/header、没有训练、没有commit或push。后续runtime可读取 `scenes` 中 `content_admission_status=accepted` 的完整candidate，只有真实reset/step及行为/容量证据完成后才单独登记后端通过。
