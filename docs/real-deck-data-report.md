# 真实最终卡组提取报告

本报告只验收 P1 数据提取及当前内容兼容性，不代表新 reset、数据划分或 PPO 已完成。

## 输入与复现

固定本地 MaT1g3R 语料；直接读取 master_deck，不读取事件前缀、历史药水或火精英身份。

- 来源：https://github.com/MaT1g3R/Slay-the-Spire-data/tree/097aaf3564c2247835162d267cbc7c55d2c9039e
- 归档 SHA256：`0b21c5fe489ac0980131d0dd14350efdf1c68f180488b6d2072ae0e81cea565e`
- 中央契约 SHA256：`cc29dad191bd560d6b4f03d048387ba2a1a41d19bb08b1ea3891dcf618e4bea5`
- 复现：`python scripts/extract-real-decks.py`
- 针对性验证：`python -m pytest -q tests/test_real_decks.py`

## 实际结果

| 指标 | 数量 |
|---|---:|
| 原始 Ironclad 文件 | 203 |
| 去重 run 组 | 157 |
| 重复别名文件 | 46 |
| 提取拒绝组 | 11 |
| 完整提取卡组 / 不同内容 | 146 / 146 |
| 完整提取中的非基础不同构筑 | 146 |
| 当前内容支持组 / 不同内容 | 0 / 0 |
| 当前内容支持的非基础不同构筑 | 0 |
| 完整提取卡牌类别 / 版本 | 114 / 196 |

基础卡组定义为未升级的5 Strike_R、4 Defend_R、1 Bash，允许额外 AscendersBane；不同卡组哈希保留重复数量与升级，忽略原数组次序。

完整提取大小分布：`{"11": 1, "14": 1, "15": 1, "16": 3, "17": 4, "18": 3, "19": 4, "20": 3, "21": 2, "22": 3, "23": 7, "24": 6, "25": 7, "26": 2, "27": 4, "28": 5, "30": 9, "31": 10, "32": 13, "33": 8, "34": 10, "35": 10, "36": 5, "37": 9, "38": 5, "39": 2, "40": 3, "41": 3, "42": 1, "43": 1, "48": 1}`。

当前支持大小分布：`{}`。

## 内容缺口

影响组数不能相加当作新增可用卡组；只有全部阻塞解除才能使用完整卡组。单项解锁数为静态估计，不替代机制验收。

| 缺口 | 影响 run 组 | 只修此项可解锁 |
|---|---:|---:|
| UNSUPPORTED_CARD:Shockwave | 76 | 0 |
| UNSUPPORTED_CARD:Burning Pact | 66 | 0 |
| UNSUPPORTED_CARD:Disarm | 66 | 0 |
| UNSUPPORTED_CARD:Offering | 65 | 0 |
| UNSUPPORTED_CARD:Armaments | 63 | 0 |
| UNSUPPORTED_CARD:Dark Embrace | 62 | 0 |
| UNSUPPORTED_CARD:Second Wind | 61 | 0 |
| UNSUPPORTED_CARD:Anger | 60 | 1 |
| UNSUPPORTED_CARD:Corruption | 58 | 0 |
| UNSUPPORTED_CARD:Headbutt | 58 | 0 |
| UNSUPPORTED_CARD:Bloodletting | 56 | 0 |
| UNSUPPORTED_CARD:Feed | 56 | 0 |
| UNSUPPORTED_CARD:Evolve | 53 | 0 |
| UNSUPPORTED_CARD:Exhume | 51 | 0 |
| UNSUPPORTED_CARD:Reaper | 51 | 0 |
| UNSUPPORTED_CARD:Fiend Fire | 49 | 0 |
| UNSUPPORTED_CARD:Barricade | 46 | 0 |
| UNSUPPORTED_CARD:Blood for Blood | 46 | 0 |
| UNSUPPORTED_CARD:Whirlwind | 38 | 0 |
| UNSUPPORTED_CARD:Dual Wield | 35 | 0 |
| UNSUPPORTED_CARD:Iron Wave | 33 | 0 |
| UNSUPPORTED_CARD:Warcry | 32 | 0 |
| UNSUPPORTED_UPGRADE:True Grit+1 | 29 | 0 |
| UNSUPPORTED_CARD:Hemokinesis | 26 | 0 |
| UNSUPPORTED_CARD:Perfected Strike | 21 | 0 |
| UNSUPPORTED_CARD:Havoc | 20 | 0 |
| UNSUPPORTED_CARD:Brutality | 20 | 0 |
| UNSUPPORTED_CARD:Double Tap | 19 | 0 |
| UNSUPPORTED_CARD:Apotheosis | 17 | 0 |
| UNSUPPORTED_CARD:Dark Shackles | 17 | 0 |
| UNSUPPORTED_CARD:PanicButton | 14 | 0 |
| UNSUPPORTED_CARD:Intimidate | 14 | 0 |
| UNSUPPORTED_CARD:Ghostly | 13 | 0 |
| UNSUPPORTED_CARD:Combust | 13 | 0 |
| UNSUPPORTED_CARD:Infernal Blade | 12 | 0 |
| UNSUPPORTED_CARD:Limit Break | 12 | 0 |
| UNSUPPORTED_CARD:Sever Soul | 12 | 0 |
| UNSUPPORTED_CARD:Rupture | 12 | 0 |
| UNSUPPORTED_CARD:Sword Boomerang | 11 | 0 |
| UNSUPPORTED_CARD:Flash of Steel | 10 | 0 |
| UNSUPPORTED_CARD:Secret Technique | 10 | 0 |
| UNSUPPORTED_CARD:Berserk | 10 | 0 |
| UNSUPPORTED_CARD:Discovery | 10 | 0 |
| UNSUPPORTED_CARD:Bite | 8 | 0 |
| UNSUPPORTED_CARD:CurseOfTheBell | 8 | 0 |
| UNSUPPORTED_CARD:Rampage | 7 | 0 |
| UNSUPPORTED_CARD:Finesse | 6 | 0 |
| UNSUPPORTED_CARD:Madness | 6 | 0 |
| UNSUPPORTED_CARD:Writhe | 6 | 0 |
| UNSUPPORTED_CARD:Fire Breathing | 6 | 0 |
| UNSUPPORTED_CARD:HandOfGreed | 5 | 0 |
| UNSUPPORTED_CARD:Juggernaut | 5 | 0 |
| UNSUPPORTED_CARD:Master of Strategy | 4 | 0 |
| UNSUPPORTED_CARD:Pain | 4 | 0 |
| UNSUPPORTED_CARD:Clumsy | 4 | 0 |
| UNSUPPORTED_CARD:Blind | 3 | 0 |
| UNSUPPORTED_CARD:Violence | 3 | 0 |
| UNSUPPORTED_CARD:Mayhem | 3 | 0 |
| UNSUPPORTED_CARD:Trip | 3 | 0 |
| UNSUPPORTED_CARD:Doubt | 3 | 0 |
| UNSUPPORTED_CARD:Necronomicurse | 3 | 0 |
| UNSUPPORTED_CARD:Dramatic Entrance | 3 | 0 |
| UNSUPPORTED_CARD:Clash | 2 | 0 |
| UNSUPPORTED_CARD:Good Instincts | 2 | 0 |
| UNSUPPORTED_CARD:Parasite | 2 | 0 |
| UNSUPPORTED_CARD:Chrysalis | 2 | 0 |
| UNSUPPORTED_CARD:Regret | 2 | 0 |
| UNSUPPORTED_CARD:Shame | 2 | 0 |
| UNSUPPORTED_CARD:Panache | 2 | 0 |
| UNSUPPORTED_CARD:Deep Breath | 2 | 0 |
| UNSUPPORTED_CARD:Secret Weapon | 2 | 0 |
| UNSUPPORTED_CARD:Bandage Up | 2 | 0 |
| UNSUPPORTED_CARD:Panacea | 2 | 0 |
| UNSUPPORTED_CARD:Magnetism | 1 | 0 |
| UNSUPPORTED_CARD:J.A.X. | 1 | 0 |
| UNSUPPORTED_CARD:Purity | 1 | 0 |
| UNSUPPORTED_CARD:Enlightenment | 1 | 0 |
| UNSUPPORTED_CARD:Injury | 1 | 0 |
| UNSUPPORTED_CARD:Decay | 1 | 0 |

### 最接近可运行的五副完整卡组

这里只展示最小联合缺口，不把一副卡组的成功当作分布完成。

| 来源组 | 张数 | 需共同补齐 |
|---|---:|---|
| run-group:857303c9b035c095e9d4 | 11 | UNSUPPORTED_CARD:Anger |
| run-group:16b38517e4242938ae88 | 18 | UNSUPPORTED_CARD:Anger、UNSUPPORTED_CARD:Madness |
| run-group:25e2d8e7d27e8b874d1e | 17 | UNSUPPORTED_CARD:Burning Pact、UNSUPPORTED_CARD:Iron Wave |
| run-group:b9056fc50a3ea89b1392 | 16 | UNSUPPORTED_CARD:Double Tap、UNSUPPORTED_CARD:Headbutt |
| run-group:bc808a84b4989749af9b | 16 | UNSUPPORTED_CARD:Combust、UNSUPPORTED_CARD:Panacea |

提取拒绝原因及组数：`{"PERMANENT_CARD_VALUE_UNRECORDED:RitualDagger": 11}`。原始卡牌列表仍完整保留，拒绝表示不能解释完整实例状态，不表示文件读取失败。

完整联合缺口、逐组卡组及拒绝原因见 real-deck-manifest.json；提取错误与运行不支持分别记录。

## 证据与下一步

逐个原文件哈希、别名、run 关联组和来源原始卡组保存在清单。标准卡牌名称严格映射，不模糊替换；缺少完整历史 mod 列表不作为全局拒绝理由，历史行为等价仍未核验。未知永久实例值和非空自定义修饰独立拒绝。

没有按玩家输赢筛选，没有删除不支持卡牌，没有把旧入口99场或新场景乘seed记成不同构筑。来源最终卡组可能跨幕；将其配置到第一幕对手属于新训练条件，不代表历史楼层。

当前全部 split=unassigned、runtime_status=not_run。P2 需锁配置与来源分组；P3 需正式 reset 准入。若支持构筑不足，优先消费联合缺口决定补哪些机制，不回到历史入口还原。
