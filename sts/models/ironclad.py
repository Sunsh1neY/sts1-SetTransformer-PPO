"""扩展Set的首批语义输入；复用已冻结QKV实现，不修改比较模型。"""
import copy

import numpy as np
from sts.env.public_battle import _canonical
from torch import nn

from sts.env.ironclad import CONTRACT, REGIONS as EXPANDED_REGIONS, CARD_BY_NAME, RUNTIME_CONTRACT, semantic_extensions
from sts.models.comparison import (
    CARD_KEYS, FEATURES, SLOTS, CARD_NUMERIC, CARD_BOOL, PLAYER, HISTORY,
    CONTRACT as BASE_ENCODING, ComparisonActorCritic, exact_keys, statuses, onehot,
)

REGIONS = EXPANDED_REGIONS[:4]

EXTRA_CARD_KEYS = {"combat_damage_bonus", "is_strike", "effective_exhaust", "cost_kind",
                   "printed_cost", "effective_cost", "effective_cost_known", "cost_scope"}
EXTRA_FEATURES = 14
ENCODING_VERSION = "ironclad-set-encoding-v2"


def encode(obs):
    """严格消费新增字段；当前64容量只适用继承内容，不是全卡生成界。"""
    if obs.get("schema") != CONTRACT["observation_schema"]:
        raise ValueError("扩展编码schema不匹配")
    if obs.get("decision") != {"phase": "NORMAL", "selection": None}:
        raise ValueError("候选头尚未验收")
    if obs.get("resolving"):
        raise ValueError("旧卡牌Set不支持选牌暂停，请使用统一实体模型")
    obs = {k: v for k, v in obs.items() if k != "resolving"}
    base = copy.deepcopy(obs)
    del base["decision"]
    del base["player"]["combust_hp_loss"]
    for region in REGIONS:
        for card in base[region]:
            if set(card) != CARD_KEYS | EXTRA_CARD_KEYS:
                raise ValueError("扩展卡牌字段变化")
        # 即使调用者构造了共享字典引用，重复牌也生成独立记录。
        base[region] = [{k: v for k, v in card.items() if k not in EXTRA_CARD_KEYS}
                        for card in base[region]]
    # 基础编码会重排非手牌；必须以同一完整公开排序绑定增量行。
    # 逐卡拼接后再排序，避免同名不同动态属性与基础行失配。
    ordered = copy.deepcopy(obs)
    for region in REGIONS[1:]:
        pairs = list(zip(base[region], ordered[region]))
        pairs.sort(key=lambda pair: _canonical(pair[0]))
        base[region] = [a for a, _ in pairs]
        ordered[region] = [b for _, b in pairs]
    result = _encode_base(base)
    extra = semantic_extensions(ordered)
    padded = np.zeros((SLOTS, EXTRA_FEATURES), dtype=np.float32)
    padded[:len(extra["cards"])] = extra["cards"]
    result["cards"] = np.concatenate([result["cards"], padded], axis=1)
    result["global"] = np.concatenate([result["global"], extra["player"]])
    if not np.isfinite(result["cards"]).all() or not np.isfinite(result["global"]).all():
        raise ValueError("扩展特征包含非有限值")
    return result


class IroncladActorCritic(ComparisonActorCritic):
    """只提供Set，新增语义从头初始化；旧权重不是精确恢复入口。"""

    def __init__(self, global_dim):
        super().__init__("set", global_dim)
        self.embedding = nn.Embedding(max(r["id"] for r in RUNTIME_CONTRACT["cards"]) + 1, 8, padding_idx=0)
        self.card_projection = nn.Sequential(nn.Linear(FEATURES + EXTRA_FEATURES + 8, 32), nn.Tanh())
        self.encoding_version = ENCODING_VERSION


def _encode_base(obs):
    exact_keys(obs, {"schema", "hand", "draw_pile", "discard_pile", "exhaust_pile", "player", "enemies", "potions", "potion_capacity", "relics", "action_mask"})
    if obs["schema"] != RUNTIME_CONTRACT["observation_schema"] or sum(len(obs[k]) for k in REGIONS) > BASE_ENCODING["card_entities"]:
        raise ValueError("观测schema或实体容量不符")
    ids = np.zeros(SLOTS, dtype=np.int64)
    features = np.zeros((SLOTS, FEATURES), dtype=np.float32)
    valid = np.zeros(SLOTS, dtype=np.bool_)
    cursor = 0
    for region, pile in enumerate(("hand", "draw_pile", "discard_pile", "exhaust_pile")):
        rows = obs[pile] if region == 0 else sorted(obs[pile], key=_canonical)
        if region == 0 and len(rows) > 10:
            raise ValueError("手牌超容量")
        for i, card in enumerate(rows):
            exact_keys(card, CARD_KEYS)
            if CARD_BY_NAME[card["name"]]["id"] != card["card_id"]:
                raise ValueError("卡牌名称与ID矛盾")
            # 手牌依实际顺序放在最前，随后紧凑放三种非手牌区；区域特征明确区分。
            # 少于10张手牌时，后面的出牌动作由环境mask关闭，不把非手牌当手牌。
            pos = cursor
            cursor += 1
            ids[pos], valid[pos] = card["card_id"], True
            if len(card["damage_by_target"]) != 5:
                raise ValueError("目标伤害缺行")
            features[pos] = ([card[k] / s for k, s in CARD_NUMERIC.items()] +
                             [float(card[k]) for k in CARD_BOOL] + [v / 50 for v in card["damage_by_target"]] +
                             onehot(card["card_type"], BASE_ENCODING["card_types"]) + onehot(region, list(range(4))) +
                             [onehot(card["target_kind"], ["NO_TARGET", "ENEMY"])[1]])
    player = obs["player"]
    exact_keys(player, set(PLAYER) | {"statuses"})
    global_values = [player[k] / s for k, s in PLAYER.items()] + statuses(player["statuses"], BASE_ENCODING["player_statuses"])
    for enemy in obs["enemies"]:
        exact_keys(enemy, {"name", "present", "targetable", "hp", "max_hp", "block", "intent_damage", "intent_hits", "intent_kind", "public_history", "statuses"})
        history = enemy["public_history"]
        exact_keys(history, set(HISTORY) | {"last_intent_kind", "previous_intent_kind"})
        global_values += [float(enemy[k]) for k in ("present", "targetable")]
        global_values += [enemy[k] / 100 for k in ("hp", "max_hp", "block", "intent_damage")]
        global_values += [enemy["intent_hits"] / 5] + onehot(enemy["name"], BASE_ENCODING["enemy_names"])
        global_values += onehot(enemy["intent_kind"], BASE_ENCODING["intent_kinds"])
        global_values += statuses(enemy["statuses"], BASE_ENCODING["enemy_statuses"])
        global_values += [history[k] / 50 for k in HISTORY]
        for key in ("last_intent_kind", "previous_intent_kind"):
            global_values += onehot(history[key], BASE_ENCODING["intent_kinds"])
    for potion in obs["potions"]:
        exact_keys(potion, {"name", "present", "potency", "target_kind", "potion_id"})
        names = [""] + [r["name"] for r in RUNTIME_CONTRACT["potions"]]
        if potion["potion_id"] != names.index(potion["name"]):
            raise ValueError("药水ID不一致")
        global_values += onehot(potion["name"], names) + [float(potion["present"]), potion["potency"] / 20,
                         onehot(potion["target_kind"], ["NO_TARGET", "ENEMY"])[1]]
    by_relic = {}
    for relic in obs["relics"]:
        exact_keys(relic, {"name", "counter", "relic_id"})
        if relic["name"] in by_relic:
            raise ValueError("重复遗物")
        by_relic[relic["name"]] = relic
    if set(by_relic) - {r["name"] for r in RUNTIME_CONTRACT["relics"]}:
        raise ValueError("未知遗物")
    for definition in RUNTIME_CONTRACT["relics"]:
        relic = by_relic.get(definition["name"])
        if relic and relic["relic_id"] != definition["id"]:
            raise ValueError("遗物ID不一致")
        counter = None if relic is None else relic["counter"]
        global_values += [float(relic is not None), float(counter is not None), (counter or 0) / 10]
    global_values += [obs["potion_capacity"] / 3]
    result = {"ids": ids, "cards": features, "valid": valid,
              "global": np.asarray(global_values, dtype=np.float32), "mask": np.asarray(obs["action_mask"], dtype=np.bool_).copy()}
    if len(obs["enemies"]) != 5 or len(obs["potions"]) != 3 or result["mask"].shape != (66,):
        raise ValueError("实体或动作维度错误")
    if not np.isfinite(features).all() or not np.isfinite(result["global"]).all():
        raise ValueError("非有限观测")
    return result
