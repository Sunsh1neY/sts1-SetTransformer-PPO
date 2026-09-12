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


def encode(obs):
    exact_keys(obs, {"schema", "hand", "draw_pile", "discard_pile", "exhaust_pile", "player", "enemies", "potions", "potion_capacity", "relics", "action_mask"})
    if obs["schema"] != PUBLIC_CONTRACT["observation_schema"] or card_count(obs) > CONTRACT["card_entities"]:
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


def tensor_batch(rows):
    return {k: torch.from_numpy(np.stack([r[k] for r in rows])) for k in rows[0]}


class AttentionBlock(nn.Module):
    """显式QKV多头注意力与残差前馈；无位置编码、无dropout。"""
    def __init__(self, width=32, heads=4):
        super().__init__()
        self.heads, self.width = heads, width
        self.q, self.k, self.v, self.out = [nn.Linear(width, width) for _ in range(4)]
        self.norm1, self.norm2 = nn.LayerNorm(width), nn.LayerNorm(width)
        self.ff = nn.Sequential(nn.Linear(width, width * 2), nn.ReLU(), nn.Linear(width * 2, width))

    def forward(self, query, keys, key_valid):
        b, n, _ = query.shape
        m, h, d = keys.shape[1], self.heads, self.width // self.heads
        q = self.q(query).reshape(b, n, h, d).transpose(1, 2)
        k = self.k(keys).reshape(b, m, h, d).transpose(1, 2)
        v = self.v(keys).reshape(b, m, h, d).transpose(1, 2)
        scores = (q @ k.transpose(-1, -2)) / d**0.5
        scores = scores.masked_fill(~key_valid[:, None, None, :], -1e9)
        attention = scores.softmax(-1) @ v
        x = self.norm1(query + self.out(attention.transpose(1, 2).reshape(b, n, self.width)))
        return self.norm2(x + self.ff(x))


class ComparisonActorCritic(nn.Module):
    def __init__(self, kind, global_dim):
        super().__init__()
        if kind not in {"mlp", "set"}:
            raise ValueError("未知编码器")
        self.kind, self.global_dim = kind, global_dim
        self.embedding = nn.Embedding(max(r["id"] for r in PUBLIC_CONTRACT["cards"]) + 1, 8, padding_idx=0)
        self.card_projection = nn.Sequential(nn.Linear(FEATURES + 8, 32), nn.Tanh())
        self.global_projection = nn.Sequential(nn.Linear(global_dim, 64), nn.Tanh())
        if kind == "mlp":
            self.encoder = nn.Sequential(nn.Linear(SLOTS * 32 + 64, 128), nn.Tanh(), nn.Linear(128, 128), nn.Tanh())
        else:
            self.sab = AttentionBlock()
            self.pool = AttentionBlock()
            self.pool_seed = nn.Parameter(torch.zeros(1, 1, 32))
            self.encoder = nn.Sequential(nn.Linear(32 + 64, 128), nn.Tanh(), nn.Linear(128, 128), nn.Tanh())
        # 共享手牌评分器把逐牌表示路由到该牌实际槽位，不把槽号塞进token。
        self.card_head = nn.Sequential(nn.Linear(128 + 32, 64), nn.Tanh(), nn.Linear(64, 5))
        self.other_head = nn.Linear(128, 16)
        self.value_head = nn.Linear(128, 1)
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)
        for head in (self.card_head[-1], self.other_head):
            nn.init.uniform_(head.weight, -0.003, 0.003)

    def forward(self, batch):
        cards = self.card_projection(torch.cat((self.embedding(batch["ids"]), batch["cards"]), -1))
        cards = cards * batch["valid"].unsqueeze(-1)
        global_value = self.global_projection(batch["global"])
        if self.kind == "set":
            valid = batch["valid"].clone()
            # 空实体集合只可能是边界夹具；避免全mask导致NaN。
            valid[~valid.any(1), 0] = True
            contextual = self.sab(cards, cards, valid)
            pooled = self.pool(self.pool_seed.expand(cards.shape[0], -1, -1), contextual, valid)[:, 0]
            z = self.encoder(torch.cat((pooled, global_value), -1))
            hand = contextual[:, :10]
        else:
            z = self.encoder(torch.cat((cards.flatten(1), global_value), -1))
            hand = cards[:, :10]
        card_logits = self.card_head(torch.cat((z[:, None].expand(-1, 10, -1), hand), -1)).flatten(1)
        logits = torch.cat((card_logits, self.other_head(z)), -1)
        return logits, self.value_head(z).squeeze(-1)

    def distribution(self, batch):
        logits, value = self(batch)
        mask = batch["mask"].clone()
        mask[~mask.any(1), 50] = True  # 仅供终局价值计算；终局不采样动作。
        return Categorical(logits=logits.masked_fill(~mask, -1e9)), value
