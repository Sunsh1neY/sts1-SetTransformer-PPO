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

## E1b：新增语义接入Set与模型边界验证（2026-09-12）

- 独立 `sts.models.ironclad` 复用冻结ComparisonActorCritic的QKV/SAB/PMA结构，仅提供Set，扩展逐牌输入6维、全局输入1维。原比较模型与训练源码哈希不变。新增语义不只停留在JSON输出。
- 同名不同实例属性保留独立行；基础字段与增量字段按相同排序对齐。当前模型沿用64位置作为继承内容开发边界，超过容量明确拒绝；这不是全卡生成/截断证明。选择阶段仍拒绝，尚无候选头。
- 首轮模型探针3项失败：重复引用夹具触发逐项删除副作用，已改为独立字典记录；另外两项测试误用未mask的forward输出，已按模型distribution接口检查合法概率与置换不变性。未修改旧模型来迁就测试。
- 复测 `python -m pytest -q tests/test_ironclad_model.py tests/test_comparison_training.py`：13 passed，7.72秒。覆盖新增各字段进入数值输入、重复实例对应、非手牌置换下合法概率/价值不变、mask、有限梯度、同版权重逐值恢复、旧维度权重拒绝和容量拒绝。
- 权重恢复测试不等于PPO collector/optimizer/RNG精确续训；后者在E3/E7接入多阶段轨迹后验收。测试内旧比较trainer的小规模更新为原有回归，不是新正式训练；未占用原30分钟正式训练预算。
- 当前准入仍69/150，新增0/81；E1整体尚未完成。下一步是E1c的费用有效期、状态实战探针与容量/候选路由，之后才可按E2批次开放新牌。

## 第一批集成复核（2026-09-12）

- 提交链：E0a `cb5aebd`；E1a `9743671`；E1b `1e0a08b`。这三个小里程碑完成，不代表E0/F0或E1整体已完成。
- 首次完整回归：696 passed、7 failed、9 errors、1 skipped；定位到独立worktree未复制被忽略的历史夹具。两份语料补齐后仍缺记录器源码与历史集成记录，继续复制必要输入；没有修改旧测试断言。
- 共复制112个历史测试输入，位于新目录reference，逐文件哈希在 `reference/expansion-test-inputs.json`；这些是历史夹具，不冒称本次新集成成绩，不提交公开语料及仲裁源码。
- 最终 `python -m pytest -q`：713 passed，25.73秒，0失败、0跳过；`python scripts/check-ironclad-expansion.py` 与 `python scripts/check-spec-v6.py` 通过；增量后端补丁反向适用检查通过。
- 对原目录起始快照200文件复核，内容均未变；冻结7项哈希不变。后续只读看到原对照报告status=complete且有4组结果；没有由本工作流停止进程，也没有据此替代原对照工作流的恢复与统计验收，F0仍待正式同步。
- 下一工作点：先完成E1c真实费用/状态探针及阶段/容量安全设计；按证据更新接口版本，进入E2时逐卡逐版本开放并记录行为测试。75类/150版本目标不降级，当前仅69版本继承准入，81新增版本仍待实现与验收。选择阶段、公开置顶记忆、生成闭包、多阶段PPO与checkpoint迁移均未完成。

## E1c：五类动态/状态卡实战探针与独立卡表（2026-09-12）

- 实现Rampage、Blood for Blood、Barricade、Corruption、Combust各基础/升级；逐实例、状态、费用以及与Strength/Burn/Metallicize/Feel No Pain/Sentinel的关联断言通过。证据、范围和未关闭组合见 docs/ironclad-dynamic-probes.md。
- 引入独立注册表，保留旧40项目ID，新卡不再受旧白名单或旧编码器卡表限制。C++新增构建指纹并由Python检查；观测v2、Set编码v2，新增印刷费与当下有效费/known/来源字段。
- 首轮两个Corruption断言失败：错误地将旧base_cost当作印刷费；源码核验其为战斗修改费，修正测试并分别保留印刷费，未改后端结算。其他探针通过。
- 标准增量构建通过；针对新增机制/继承入口/新旧模型的回归121项通过（正式训练未启动）。
- 准入从69增至79/150，新增10/81版本通过当前范围验收；这五类的选牌/复制关联仍依赖后续阶段，E1/E4/E5整体均不宣称完成。
- 当前容量证明仅覆盖旧内容加五类不生成卡探针；下一步加入在完整决策点切段的独立采集包装，拒绝超初始容量，不丢final_obs实体。

## E1d：完整决策点容量采集与受控集成（2026-09-12）

- E1c提交为 `3533207`。本小步新增 `sts.env.ironclad_collection.IroncladCollectionEnv` 和独立容量契约，64实体/50阈值/15余量，初始<=49、最大512动作。超界初态整副拒绝，不删牌。注册表或运行契约变化时必须重做证明。
- C++单独导出累计分配计数用于info；Power从四区消失不回收ID。每步检查实际分配增长，完整结算后才截断，保存原合法mask；同时记录决策、出牌、回合结束及药水次数，选择次数当前为0。
- 6项容量专测通过：真实Power Through由49到51实体切段、最终观测完整编码；真实Set最终价值传入既有GAE，验证自举且不跨reset；两预算同时触发、Power数量与累计ID区别、reset失败失效、内容hash漂移拒绝。
- `python scripts/diagnose-ironclad-expansion.py --output reference/ironclad-integration-e1d.json`：100局、1919个transition，99自然结束、1容量截断、0异常/非法动作，随机策略19胜；最大52实体，耗时5.56秒。夹具为五类×两版本×五遭遇×两配置，明确为合成受控卡组，不是人类真实卡组或学习收益证据。
- 唯一截断为Rampage夹具的Three Sentries，原因external_card_capacity；截断不计作失败。每个过程状态及最终状态都执行Set编码完整性检查。原始种子/动作轨迹、代码/后端/契约指纹已落在上述被忽略报告；报告SHA256为 `a4492e11d80cc7cdc6501b53d65d1c9b2ec2557f9a9cab5cf8af50c21b26600e`。
- 最终全仓 `python -m pytest -q`：751 passed，25.02秒，0失败/0跳过；规格及覆盖台账检查通过，冻结7项哈希不变。标准增量构建与补丁反向适用检查通过。
- 原目录只读核对发现6份文档相对初始化快照已有更新：AGENTS.md、spec-v6.md、docs/decisions.md、docs/comparison-m3-training.md、docs/real-deck-training-plan.md、docs/week-5-6-plan.md；本工作流未写这些原目录文件，未覆盖或自动合并。原AGENTS已记录对照收口与4份checkpoint恢复，扩展分支F0最终归档同步仍单独处理。
- 当前79/150版本，余71版本；E1中的阶段路由/公开记忆与更多费用语义仍未完成，本次不宣称E1或全卡完成。下一步进入真实选牌阶段接口骨架和路由验证，保持多候选不自动代选，随后推进E2/E3及剩余批次。正式扩展PPO/checkpoint迁移仍待后续。
