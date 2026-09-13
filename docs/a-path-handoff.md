# A路径续接记录

## 2026-09-13压缩后更新（优先于下方旧快照）

- 用户已追加基准commit/push授权；main与远端均615cffa，基准已发布。下方“不push”是旧授权历史。
- A路径模型与Agent首批验收已实施，见a-path-model-milestone.md及a-path-inventory.md；模型不再是未测试草稿。全仓1265通过，随后数据审计2项、独立C++夹具1项分别通过。
- 当前尚未正式采集、PPO更新闭环、完整恢复或新训练；四小时预算未开始。
- 新数据范围待裁决见a-path-data-decision.md：A保留13条中途训练候选，B增加47份静态合格最终卡组候选并逐项准入（关联后29份在训练侧、18份开发侧）。裁定前不冻结正式池或训练。
- 下方为压缩时原始快照，保留历史来源与环境重建细节。

日期：2026-09-13。用户最新要求：正式进入a-path-agent之前先压缩上下文，因此当前暂停实现。此文件是续接事实，不是A路径验收报告。

## 用户授权和目标

- 用户明确要求完整执行已确认计划：保存成果→独立集成环境→回归后合入main→A路径→工程验收→受限训练/评估→本地合入main。不push。
- 新需求以仓库根目录a-path/sts-a-path-implementation-v1.md和codex-astra-agent-prompt.md为准，路径不是包中旧的agent-tasks/a-path。
- 用户明确选择四层SAB、64维、4头、FF128、Pre-LN、GELU、dropout0、FP32、一个seed的PMA。不重新询问A/B或层数。
- 来源task Query统一softmax（牌/药水/特殊操作）；所选来源生成目标Query，仅在合法敌人上softmax；NO_TARGET概率1；一次编码、一次真实env.step；真正结算后的选牌阶段新观测新决策。
- PPO联合logp、一个ratio和clipping、精确联合熵。显式采样RNG、不可变历史观测/mask/路由，更新重算编码，真实终止/外部截断自举不变。
- 工程通过后1初始化32768 transition smoke；最多3初始化各累计262144步；首次smoke计入总步数，LR按总预算；最多一次有证据修正和额外32768步。训练评估总计最多4小时，预留评估和保存。
- 不增DT/非战斗Agent/RunEnv/未准入敌人，不改奖励或eval_seeds，不购买算力、不下载大型归档。保持旧MLP/Set结果和辅助worktree。
- 不自动使用subagent：当前开发指令禁止无明确授权主动委派，本轮执行尚未使用subagent。

## 工作区与提交

- 主工作区C:/Users/19091/Desktop/sts2，main目前fdde4c0（已同步文档去重修复），无未提交代码。主工作区ignored后端仍是原实验构建，尚未迁移到集成后端；不要宣称main的扩展运行已就绪。
- 执行工作区C:/Users/19091/Desktop/sts2-integration，目前分支codex/a-path-agent，HEAD fdde4c0。沿用已经干净重建的独立后端，避免重复建worktree/编译。
- codex/environment-integration指向8c861d5。环境代码已合入main；后续dc9d55b/fdde4c0仅修复文档完整性与重复。
- 原main未提交40文件保存为fd90b58；原全卡2325d55干净；原敌人未提交38文件保存为406875a。全卡和敌人原worktree保留，A–D辅助分支未合入。
- c454fa8合全卡，31343cb合敌人，8c861d5环境修复与验收。没有push。
- 初始快照：主目录runs/environment-integration-20260913/source-manifest.json与两个工作区差异补丁；已跟踪来源docs/environment-integration-sources.json。
- 当前执行目录未提交草稿：sts/models/apath.py；此续接记录也是新文件。不要丢弃，也不要将草稿称为实现已验收。

## 环境验收完成情况

- 锁定C++上游7476a81954020087da31d41d16fddf475746ec2d；json=0b345b20c888f7dc8888485768e4bf9a6be29de0；pybind11=a2e59f0e7065404b44dfe92a28aca47ba1378dc4。
- 在sts2-integration/third_party/sts_lightspeed从本地源clone干净版本，依次应用lightspeed-battle-env.patch、lightspeed-enemy-potion.patch。敌人集成增量已经包含全卡变更，不再叠加lightspeed-ironclad-expansion.patch。
- build-enemy-potion.ps1补上generate-public-contract.py。以原main/.venv-gpu/Scripts/python.exe、Jobs1构建成功；生产pyd来自执行目录build，非其他worktree。
- 回归命令python -X utf8 -m pytest -q --ignore=tests/test_enemy_status_export.py --tb=short：最终1244 passed in 54.60s，日志runs/environment-integration/cpu-final.txt。
- 单独python -X utf8 -m pytest -q tests/test_enemy_status_export.py：1 passed in 2.83s。与1244分开记，不冒称一次1245。
- 定向155 passed in 12.64s。第一轮91 failed/1144 passed/9 errors记录保留cpu-regression.txt，不覆盖为成功。spec检查PASS，git diff --check通过。
- 第一轮失败修复：旧整数route断言适配snapshot封装；旧卡牌Set原型不再伪造已删除的旧意图类别（编码版本ironclad-set-encoding-v3-history-counts）；只比较旧观测共同字段，终局明确验证新敌人清理；Fiend Fire夹具保留Explosive Potion让非终局伤害可读，基础/升级精确伤害及5牌耗尽通过。
- 冻结sts/env/public_battle.py从main保持；新全卡使用full_card_public.py。原MLP/comparison模型未改。
- 历史容量器显式限定原5遭遇，不自动承接29遭遇的旧15生成界；card_count包含stasis；NORMAL封装正确计出牌/结束/药水，不误计selection。容量JSON已重绑当前集成后端及契约指纹，但training_admitted仍false。
- ignored测试资料已从main复制：reference/public-run-corpus固定zip、corpus.json、recorder-source以及reference/public-scene-integration.json。
- scripts/audit-public-corpus.py历史SHA=c9dc6fb6f990192b40856b3eb03dc58801ab534db4974d6387cabf111a2c3e09依赖原混合换行；原始字节从main核验复制，.gitattributes为该文件-text whitespace=cr-at-eol。不可统一格式化再更新历史清单凑通过。
- 合并文档第一次处理丢失尾部，随后修复引入重复；最终fdde4c0按独立标题合并，decisions702行/spec777行，spec检查PASS。相关原始完整文档始终在fd90b58/2325d55/406875a可追溯。

## 当前接口事实和缺口

- 统一全卡IroncladEnv是150卡牌版本、A20、29跨幕入口（第二幕22），8遗物/15药水。独立EnemyPotion入口另有自己的35牌/药水/敌人范围，不能求并集当训练白名单。
- 统一编码sts/env/entities.py：CARD116、ENEMY774；PLAYER_GLOBAL含阶段/selection_kind，但resolution_context目前只在候选，不在实体。holds_card融合为零初始化无bias Linear65→64；stasis仅公开牌名，其他属性未知，引用不进入语义。
- EntitySample含tokens/candidates/routes/held_card_index；Candidate(kind,source,target,legal,context)。NORMAL routes是{kind:NORMAL,snapshot,action}；SELECT_CARD routes是{kind:SELECT_CARD,decision_id,candidate_index}。
- SELECT_CARD候选的旧target指向效果来源牌/药水，绝不是敌人目标；A路径对此必须NO_TARGET，操作语义来自selection_kind。同一场景当前candidate.context一致。
- 现有选择为6种真实单选；DISCOVERY仅合成接口测试，实际环境明确拒绝；多选/确认未接入，不能说支持。
- sts/models/entities.py仍为两层64维均值池化历史模型；主目录sts/models/unified.py四层PMA但只覆盖旧冻结内容且旧全局动作头。新A路径复用EntityBlock和最新实体，保留历史模块。
- IroncladEnv.reset仍明确只允许diagnostic=True/purpose=development。正式训练必须新建严格版本化准入入口，不能把训练包装为diagnostic。
- 目前没有完整A路径采集器/更新/checkpoint/正式数据池/恢复。旧sts/train/comparison.py、unified.py可复用GAE和流程；旧entitycheckpoint仅无活动环境更新边界，不满足A路径。
- 若无C++快照，恢复采用完整场景/seed/动作序列重放，校验语义观测与候选，再重新绑定随机路由凭据；checkpoint需要保存所有RNG和运行指纹。
- 旧真实卡组sts/env/real-deck-batch.json含27内容/75run，92条卡组、两配置、5遭遇；旧65train/10development存在4内容重叠。新池必须按run/seed/重复内容连通分组，不将旧开发当新heldout；已有可信真实最终卡组manifest可查，缺永久数值不补造。

## A路径未测试草稿

sts/models/apath.py刚写入，尚未import/测试。包括ActionSample、adapt/encode、batch_samples、masked_logprobs、JointDistribution、APathActorCritic；四层EntityBlock、关系融合、PMA、task Query/来源Key、目标Query/Key、特殊动作头、Value；act/evaluate_actions/value_only。

续接必须逐项审阅而不是直接训练：空候选collate兼容、来源分组唯一性、操作语义、padding、终局Value-only、上下文进入玩家token、历史logp复算、梯度、显式RNG、关系引用验证、性能与全部T01–T32。

## 下一步执行顺序

1. 读此记录和实际a-path任务书/fixture，查看git status与草稿；补docs/a-path-inventory.md，维护I0裁定（已有，无需重新请求用户批准）。
2. 审阅/修复模型草稿并写真实数学/路由/置换/梯度测试。独立数学脚本仅证明fixture；命令python a-path/verify-a-path-math.py --require-autograd，不覆盖包内历史报告。
3. 建立正式场景准入、完整观测容量及数据划分；不静默删牌/实体；复用已核验范围。
4. 实现两阶段Agent、on-policy collector、PPO更新、微批/梯度累积、checkpoint与活动环境精确重放；测试CPU/CUDA下一动作和下一更新。
5. 真实环境闭环和资源预检通过后受限训练；从训练开始计四小时而不是从工程开始。显式报告数据范围、所有初始化、随机/规则适用切片和未训练模型对照。
6. 完成A路径报告和真实学习样例；确认最终代码与文档后本地合main，并处理main后端运行一致性（保护旧后端/实验快照，不能旧pyd配新扩展代码冒称可运行）。不push。

原用户要求持续完成全计划；本次仅因用户要求上下文压缩而停在续接点，不代表完成。
