# 环境集成验收

2026-09-13。独立工作区sts2-integration；集成来源见environment-integration-sources.json。main未提交成果保存为fd90b58；全卡2325d55；敌人未提交成果保存为406875a。辅助worker未直接合入，未push。

## 实现

采用锁定上游及锁定json/pybind11，从干净本地clone应用冻结基础补丁和敌人集成增量；36项构建计划完成slaythespire目标和导入。补齐干净构建需要的public契约头生成。全卡增量保留历史用途，不与集成增量重复叠加。

统一扩展保留150卡牌版本、全卡29遭遇（第二幕22）、8遗物/15药水的既有开发边界。独立EnemyPotion入口保留自己的35牌及药水/遭遇范围，不把两入口白名单求并集作为训练准入。CARD116、ENEMY774、holds_card、stasis未知值遮罩、公开阶段、快照路由和battle_exit保留。

冻结public Python适配器保持主线；扩展走full_card_public。旧卡牌Set原型版本升级为ironclad-set-encoding-v3-history-counts，仅兼容原敌人且无关系/无选择场景，不伪造已删除的旧意图类别历史；MLP与既有比较模型不改。新A路径尚未实施。

历史容量采集器显式限制原五遭遇，避免将旧每步生成界自动扩大到新敌人；累计编号保护、资源异常和完整状态保留。普通snapshot动作正确区分出牌/结束/药水计数。当前开发采集资源指纹重绑于实际新编译模块，仍不批准正式训练。新增敌人采用完整决策点工程测试，未来训练准入另验。

## 验证

首轮全仓：91失败、1144通过、9错误；未将其冒称通过。失败归因包括旧整数路由断言、旧意图类别字段、终局敌人清理、历史模型兼容和ignored资料缺失。Fiend Fire使用保留药水动作的非终局夹具继续精确验证4次伤害和5牌耗尽。旧版对拍比较共同公开字段，终局额外验证集成版敌人清理。

定向155项通过；生产C++状态导出夹具独立1项通过。完整CPU回归1244通过（54.60秒），0失败/跳过；与单独C++夹具1通过分开记录。spec检查PASS，git diff --check通过。历史审计脚本原始混合换行SHA由原工作区核验并保留，.gitattributes禁止对该文件转换；未更新历史清单来掩盖哈希漂移。

## 复现与限制

运行scripts/build-enemy-potion.ps1 -Python <本机Python> -Jobs 1；python -X utf8 -m pytest -q --ignore=tests/test_enemy_status_export.py；单独运行后者避免编译压力。reference/public-run-corpus下的固定归档、recorder-source及corpus.json和public-scene-integration.json是既有ignored测试依赖，须从记录来源复制并核验。

既有历史checkpoint仍须在对应源代码/依赖快照恢复，当前新后端不伪装为旧精确续训。此报告不证明完整RunEnv、所有组合、训练收益或泛化。
