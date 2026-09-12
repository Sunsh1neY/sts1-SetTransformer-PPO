"""公开战斗规则基线：只读规范观测，用可解释近似评分选择合法动作。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import json
from pathlib import Path

import numpy as np

from sts.agents.masked_policy import AgentDecision

_CONTRACT = json.loads((Path(__file__).parents[1] / "env/public-battle-contract.json").read_text(encoding="utf-8"))
PUBLIC_SCHEMA = _CONTRACT["observation_schema"]
PUBLIC_ACTION_COUNT = _CONTRACT["action_count"]
END_TURN = _CONTRACT["end_turn"]
if (PUBLIC_ACTION_COUNT, END_TURN, _CONTRACT["capacity"]["targets"]) != (66, 50, 5):
    raise ValueError("规则策略尚未实现新的动作布局")


def _name(value: str) -> str:
    return "".join(char.lower() for char in value if char.isalnum())


CARD_NAMES = frozenset(map(_name, (
    "Strike", "Strike_R", "Defend", "Defend_R", "Bash", "Bludgeon", "Cleave",
    "Clothesline", "Twin Strike", "Thunderclap", "Uppercut", "Body Slam",
    "Entrench", "Heavy Blade", "Spot Weakness", "Inflame", "Pommel Strike",
    "Shrug It Off", "Dropkick", "Carnage", "Ghostly Armor", "Impervious", "Pummel",
    "Seeing Red", "Sentinel", "True Grit", "Battle Trance", "Flex", "Metallicize",
    "Demon Form", "Rage", "Flame Barrier", "Feel No Pain", "Wild Strike",
    "Reckless Charge", "Power Through", "Immolate", "Ascenders Bane", "Wound",
    "Dazed", "Burn", "Slimed",
)))
RELIC_NAMES = frozenset(_name(entry["name"]) for entry in _CONTRACT["relics"])
POTION_NAMES = frozenset(map(_name, (
    "Weak Potion", "Regen Potion", "EssenceOfSteel", "Explosive Potion", "Ancient Potion",
    "FearPotion", "LiquidBronze", "Energy Potion", "SpeedPotion", "Dexterity Potion",
    "HeartOfIron", "Fruit Juice", "Block Potion", "Strength Potion", "Swift Potion",
)))


def _number(value: Any, field: str, *, minimum: float | None = None) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.number)):
        raise TypeError(f"{field} 必须是有限数值")
    result = float(value)
    if not np.isfinite(result) or (minimum is not None and result < minimum):
        raise ValueError(f"{field} 数值域无效")
    return result


def _status(entity: Mapping[str, Any], name: str) -> float:
    return next((float(amount) for key, amount in entity["statuses"].items()
                 if _name(key) == _name(name)), 0.0)


def validate_public_observation(observation: Mapping[str, Any]) -> np.ndarray:
    """拒绝未知协议和残缺输入；不改变 mask，也不读观测之外的对象。"""
    if observation["schema"] != PUBLIC_SCHEMA:
        raise ValueError("未知公开观测 schema")
    mask = np.asarray(observation["action_mask"])
    if mask.shape != (PUBLIC_ACTION_COUNT,) or mask.dtype != np.bool_:
        raise ValueError("公开 action_mask 必须是 66 位 bool")
    if not mask.any():
        raise ValueError("没有合法动作")
    hand, enemies, potions = (observation[key] for key in ("hand", "enemies", "potions"))
    if not isinstance(hand, list) or len(hand) > 10 or len(enemies) != 5 or len(potions) != 3:
        raise ValueError("公开观测实体容量不匹配")
    player = observation["player"]
    for key in ("hp", "max_hp", "block", "energy", "energy_per_turn", "turn", "ascension"):
        _number(player[key], f"player.{key}", minimum=0)
    if player["max_hp"] <= 0 or player["hp"] > player["max_hp"]:
        raise ValueError("玩家 HP 超出范围")
    for entity in [player, *enemies]:
        if not isinstance(entity["statuses"], Mapping):
            raise TypeError("statuses 必须是公开状态映射")
        for key, value in entity["statuses"].items():
            _number(value, f"statuses.{key}")
    for enemy in enemies:
        for key in ("present", "targetable"):
            if not isinstance(enemy[key], (bool, np.bool_)):
                raise TypeError(f"enemy.{key} 必须是 bool")
        for key in ("hp", "max_hp", "block", "intent_damage", "intent_hits"):
            _number(enemy[key], f"enemy.{key}", minimum=0)
        if enemy["targetable"] and not enemy["present"]:
            raise ValueError("不存在敌人不能作为目标")
        enemy["name"], enemy["intent_kind"]
    for slot, card in enumerate(hand):
        name = _name(card["name"])
        if name not in CARD_NAMES:
            raise ValueError(f"未注册规则卡牌 {card['name']}")
        for key in ("card_id", "upgrade_count", "damage", "block", "magic", "hits"):
            _number(card[key], f"card.{key}")
        _number(card["cost"], "card.cost")
        if card["cost"] < 0 and mask[slot * 5:slot * 5 + 5].any():
            raise ValueError("负费用哨兵卡不得有可执行动作")
        if card["cost_known"] is not True:
            raise ValueError("手牌费用必须已知")
        if name == "truegrit" and card["upgrade_count"] != 0:
            raise ValueError("True Grit 升级版需要选择协议")
        if name in ("ascendersbane", "wound", "dazed", "burn") and mask[slot * 5:slot * 5 + 5].any():
            raise ValueError("不可打状态或诅咒不能有合法打出动作")
        if card["target_kind"] not in ("ENEMY", "NO_TARGET"):
            raise ValueError("未知卡牌目标协议")
        preview = card["damage_by_target"]
        if len(preview) != 5:
            raise ValueError("伤害预览必须对应五个敌人行")
        for value in preview:
            _number(value, "damage_by_target", minimum=0)
        for target in np.flatnonzero(mask[slot * 5:slot * 5 + 5]):
            if card["target_kind"] == "ENEMY" and not enemies[target]["targetable"]:
                raise ValueError("mask 指向不可选敌人")
            if card["target_kind"] == "NO_TARGET" and target != 0:
                raise ValueError("无目标牌 mask 目标列无效")
    if mask[len(hand) * 5:50].any():
        raise ValueError("mask 指向不存在手牌槽位")
    for slot, potion in enumerate(potions):
        if not isinstance(potion["present"], (bool, np.bool_)):
            raise TypeError("potion.present 必须是 bool")
        if potion["present"]:
            if _name(potion["name"]) not in POTION_NAMES:
                raise ValueError(f"未注册规则药水 {potion['name']}")
            _number(potion["potency"], "potion.potency", minimum=0)
            if potion["target_kind"] not in ("ENEMY", "NO_TARGET"):
                raise ValueError("未知药水目标协议")
        for target in np.flatnonzero(mask[51 + slot * 5:56 + slot * 5]):
            if not potion["present"]:
                raise ValueError("mask 指向空药水槽位")
            if potion["target_kind"] == "ENEMY" and not enemies[target]["targetable"]:
                raise ValueError("药水 mask 指向不可选敌人")
            if potion["target_kind"] == "NO_TARGET" and target != 0:
                raise ValueError("无目标药水 mask 目标列无效")
    for relic in observation["relics"]:
        if _name(relic["name"]) not in RELIC_NAMES:
            raise ValueError(f"未注册规则遗物 {relic['name']}")
        if relic["counter"] is not None:
            _number(relic["counter"], "relic.counter")
    return mask


def _damage_value(enemy: Mapping[str, Any], per_hit: float, hits: float) -> float:
    """公开预览的保守短视价值；多段防护触发只作近似，不宣称精确模拟。"""
    dealt = max(0.0, per_hit * hits - enemy["block"])
    hp_damage = min(enemy["hp"], dealt)
    # Curl Up 会在伤害中途补盾，因此多段时不声称确定击杀。
    lethal = dealt >= enemy["hp"] and enemy["hp"] > 0
    lethal = lethal and not (hits > 1 and _status(enemy, "Curl Up") > 0)
    threat = enemy["intent_damage"] * enemy["intent_hits"]
    return hp_damage + (12.0 + 1.25 * threat if lethal else 0.0)


def score_public_actions(observation: Mapping[str, Any]) -> np.ndarray:
    """返回合法动作的解释性效用，非法动作保持负无穷。"""
    mask = validate_public_observation(observation)
    scores = np.full(PUBLIC_ACTION_COUNT, -np.inf, dtype=np.float64)
    player, enemies, hand = (observation[key] for key in ("player", "enemies", "hand"))
    active = [index for index, enemy in enumerate(enemies) if enemy["targetable"]]
    incoming = sum(enemies[index]["intent_damage"] * enemies[index]["intent_hits"] for index in active)
    unmet = max(0.0, incoming - player["block"])
    attack_hits = sum(max(0, card["hits"]) for card in hand if card["damage"] > 0)
    draw_room = max(0, 10 - len(hand) + 1)
    can_draw = _status(player, "No Draw") <= 0

    def block_value(amount: float) -> float:
        return 1.1 * min(unmet, max(0, amount))

    for action in np.flatnonzero(mask):
        if action == END_TURN:
            scores[action] = 0.0
            continue
        if action < END_TURN:
            slot, target = divmod(int(action), 5)
            card = hand[slot]
            name, magic = _name(card["name"]), max(0, card["magic"])
            targets = active if name in ("cleave", "thunderclap", "immolate") else [target]
            value = -0.25 * card["cost"]
            if card["damage"] > 0 or name == "bodyslam":
                for index in targets:
                    enemy = enemies[index]
                    value += _damage_value(enemy, card["damage_by_target"][index], max(1, card["hits"]))
                    value -= max(1, card["hits"]) * max(0, _status(enemy, "Thorns"))
            value += block_value(card["block"])
            if name == "entrench":
                value += block_value(player["block"])
            draws = magic if name in ("pommelstrike", "battletrance") else 1 if name == "shrugitoff" else 0
            if name == "dropkick" and _status(enemies[target], "Vulnerable") > 0:
                draws += 1
                value += 4
            value += 3 * min(draw_room, draws) if can_draw else 0
            if name == "seeingred":
                value += 4 * max(2, magic)
            if name in ("inflame", "flex", "spotweakness", "demonform"):
                condition = name != "spotweakness" or enemies[target]["intent_hits"] > 0
                if condition:
                    value += magic * max(1, min(4, attack_hits)) * (0.8 if name == "flex" else 1.5)
            if name in ("bash", "thunderclap", "uppercut", "clothesline"):
                for index in targets:
                    if _status(enemies[index], "Artifact") <= 0:
                        value += min(6, magic * 2)
            if name in ("metallicize", "feelnopain", "rage"):
                value += magic * 1.5
            if name == "flamebarrier":
                value += magic * sum(enemies[index]["intent_hits"] for index in active)
            if name in ("wildstrike", "recklesscharge", "immolate"):
                value -= 1.5
            if name == "powerthrough":
                value -= 3
            if name == "truegrit":
                value -= 1.5
                value += _status(player, "Feel No Pain")
            if name == "slimed":
                value += 0.5
            # Nob 的公开 Enrage 是技能牌机会成本；不预测其未来动作。
            if card["damage"] <= 0 and name not in ("inflame", "demonform", "metallicize", "feelnopain"):
                value -= sum(max(0, _status(enemies[index], "Enrage")) for index in active)
            scores[action] = value
        else:
            slot, target = divmod(int(action) - 51, 5)
            potion = observation["potions"][slot]
            name, potency = _name(potion["name"]), potion["potency"]
            value = -1.0  # 单战斗内保留药水的有限机会成本。
            if name in ("firepotion", "explosivepotion"):
                for index in active if name == "explosivepotion" else [target]:
                    value += _damage_value(enemies[index], potency, 1)
            elif name == "blockpotion":
                value += block_value(potency)
            elif name == "strengthpotion":
                value += potency * max(1, min(4, attack_hits))
            elif name in ("dexteritypotion", "speedpotion"):
                value += potency * sum(card["block"] > 0 for card in hand)
            elif name == "energypotion":
                value += 4 * min(potency, max(0, sum(card["cost"] for card in hand) - player["energy"]))
            elif name == "swiftpotion":
                value += 3 * min(potency, max(0, 10 - len(hand))) if can_draw else 0
            elif name in ("fearpotion", "weakpotion"):
                value += potency * 2 if _status(enemies[target], "Artifact") <= 0 else 0
            elif name == "regenpotion":
                value += min(player["max_hp"] - player["hp"], potency * (potency + 1) / 2)
            elif name == "essenceofsteel":
                value += potency * 2
            elif name == "heartofiron":
                value += potency * 2
            elif name == "liquidbronze":
                value += potency * sum(enemies[index]["intent_hits"] for index in active)
            elif name == "ancientpotion":
                value += potency * (3 if any(enemies[index]["intent_kind"] in ("DEBUFF", "ATTACK_DEBUFF") for index in active) else 1)
            elif name == "fruitjuice":
                value += potency
            scores[action] = value
    return scores


class RuleAgent:
    """每步重新评分；分数平局用最小合法编号，不使用环境随机流。"""

    policy_version = "public-rule-v1"

    def decide(self, observation: Mapping[str, Any]) -> AgentDecision:
        scores = score_public_actions(observation)
        action = int(np.argmax(scores))
        probabilities = np.zeros(PUBLIC_ACTION_COUNT, dtype=np.float64)
        probabilities[action] = 1.0
        return AgentDecision(probabilities=probabilities, action=action)
