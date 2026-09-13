"""逐卡等信息MLP与Set Actor-Critic；槽位仅用于输出路由。"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical

from sts.env.comparison import card_count, load_contract
from sts.env.public_battle import CARD_BY_NAME, PUBLIC_CONTRACT, _canonical

CONTRACT = load_contract()
SLOTS = CONTRACT["card_entities"]
CARD_NUMERIC = {"upgrade_count": 1, "base_cost": 3, "cost": 3, "damage": 50, "block": 50,
                "base_block": 50, "magic": 10, "hits": 5}
CARD_BOOL = ("cost_known", "all_enemies", "ethereal", "exhaust", "free_to_play_once", "retain")
PLAYER = {"hp": 100, "max_hp": 100, "block": 100, "energy": 3, "energy_per_turn": 3,
          "turn": 50, "ascension": 20, "cards_played_this_turn": 10,
          "attacks_played_this_turn": 10, "skills_played_this_turn": 10}
HISTORY = ("completed_enemy_turns", "charge_turns_observed", "sleep_turns_observed")
CARD_KEYS = set(CARD_NUMERIC) | set(CARD_BOOL) | {"card_id", "name", "card_type", "target_kind", "damage_by_target"}
FEATURES = len(CARD_NUMERIC) + len(CARD_BOOL) + 5 + 5 + 4 + 1


def exact_keys(obj, expected):
    if set(obj) != set(expected):
        raise ValueError(f"观测字段变化：{set(obj) ^ set(expected)}")


def onehot(value, choices):
    if value not in choices:
        raise ValueError(f"未知类别：{value}")
    return [float(value == c) for c in choices]


def statuses(values, names):
    if set(values) - set(names):
        raise ValueError(f"未知状态：{set(values) - set(names)}")
    # 显式保留存在标志；公开0与未出现不合并。
    return [x for name in names for x in (float(name in values), values.get(name, 0) / 10)]


def encode_fields(obs):
    SLOTS = max(1, card_count(obs))
    exact_keys(obs, {"schema", "hand", "draw_pile", "discard_pile", "exhaust_pile", "player", "enemies", "potions", "potion_capacity", "relics", "action_mask"})
    if obs["schema"] != PUBLIC_CONTRACT["observation_schema"]:
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
                             onehot(card["card_type"], CONTRACT["card_types"]) + onehot(region, list(range(4))) +
                             [onehot(card["target_kind"], ["NO_TARGET", "ENEMY"])[1]])
    player = obs["player"]
    exact_keys(player, set(PLAYER) | {"statuses"})
    global_values = [player[k] / s for k, s in PLAYER.items()] + statuses(player["statuses"], CONTRACT["player_statuses"])
    for enemy in obs["enemies"]:
        exact_keys(enemy, {"name", "present", "targetable", "hp", "max_hp", "block", "intent_damage", "intent_hits", "intent_kind", "public_history", "statuses"})
        history = enemy["public_history"]
        exact_keys(history, set(HISTORY) | {"last_intent_kind", "previous_intent_kind"})
        global_values += [float(enemy[k]) for k in ("present", "targetable")]
        global_values += [enemy[k] / 100 for k in ("hp", "max_hp", "block", "intent_damage")]
        global_values += [enemy["intent_hits"] / 5] + onehot(enemy["name"], CONTRACT["enemy_names"])
        global_values += onehot(enemy["intent_kind"], CONTRACT["intent_kinds"])
        global_values += statuses(enemy["statuses"], CONTRACT["enemy_statuses"])
        global_values += [history[k] / 50 for k in HISTORY]
        for key in ("last_intent_kind", "previous_intent_kind"):
            global_values += onehot(history[key], CONTRACT["intent_kinds"])
    for potion in obs["potions"]:
        exact_keys(potion, {"name", "present", "potency", "target_kind", "potion_id"})
        names = [""] + [r["name"] for r in PUBLIC_CONTRACT["potions"]]
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
    if set(by_relic) - {r["name"] for r in PUBLIC_CONTRACT["relics"]}:
        raise ValueError("未知遗物")
    for definition in PUBLIC_CONTRACT["relics"]:
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

