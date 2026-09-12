# 全卡扩展实施记录

每个小里程碑独立提交；提交号由 `git log -- docs/ironclad-expansion-progress.md` 查得，避免记录自身提交号造成循环。未列为通过的阶段保持未完成。

## E0a：隔离版本与覆盖台账（2026-09-12）

- 基线：独立目录 `sts2-full-card`，分支 `codex/ironclad-full-expansion`，起始快照 `50b756e`。原对照报告在检查时仍为 running；F0最终冻结与同步未完成。
- 用户授权独立开发并行，已登记决策与规格增补；不启动额外训练。
- 新建独立扩展契约与150版本覆盖台账，81个缺失版本逐项分配E2–E6；35类69版本继承状态与扩展接口验收分开。新接口初始验收0/150，不代表旧接口失效。
- 冻结7个文件哈希：旧public/对照/真实批次契约、对照模型及训练实现、旧后端补丁和eval_seeds。新后端修改使用增量补丁。
- 验证：`python scripts/check-ironclad-expansion.py` 检查150唯一版本、批次分配、证据路径和冻结哈希；`python scripts/check-spec-v6.py` 检查规格。
- 未完成：E0中的F0最终冻结；E1–E7尚待实施。50–90小时为原估算，本小步不足以重估全量工期。

## E1a：独立后端入口与具名动态字段（2026-09-12）

- 新增 C++ `IroncladExpandedBattleEnv` 和 Python `sts.env.ironclad.IroncladEnv`；旧Public入口的schema与字段不变。Python旧包装仅抽取可覆写规范化方法。
- 新观测明确 NORMAL 阶段、无选择对象；新增实例增伤、Strike类别、费用类别、有效耗尽及Combust失血字段。旧内容以外仍拒绝，正式训练/旧数据自动迁移仍关闭。
- Barricade/Corruption的布尔导出分支已实现；Rampage增伤读取具名值。对应牌尚未准入，因此这些路径只记实现、未通过实战机制验收，不宣称R02/R03关闭。当前不导出非手牌临时费用或隐藏ID。
- 后端差异保存 `patches/lightspeed-ironclad-expansion.patch`，基础补丁不变；构建脚本新增显式ExtraPatch参数，不传参数仍走旧流程。
- 标准独立构建通过：`./scripts/build-lightspeed.ps1 -Python ./.venv/Scripts/python.exe -Jobs 1 -ExtraPatch ./patches/lightspeed-ironclad-expansion.patch`。全新本地CMake缓存，单编译任务，无GPU训练。
- `python -m pytest -q tests/test_ironclad_expansion.py tests/test_public_battle.py tests/test_real_deck_batch.py`：98 passed，5.14秒。新增76项，其中69个继承版本逐动作对照新旧入口，检查完整四区、mask、奖励、终止与截断final_obs。其余验证语义可辨识、隐藏字段拒绝、未验收卡及训练拒绝。
- 扩展接口继承准入69/150，新增准入0/81。此对照证明适配器不改变旧行为，不是对正版150版本的独立机制校准。
- E1未完成：费用有效期、真实动态/状态组合、候选路由和全卡容量证明；E2–E7未完成。下一小步把新增语义接入独立Set编码并验证输出与梯度。
