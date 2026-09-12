"""扩展Set的首批语义输入；复用已冻结QKV实现，不修改比较模型。"""
import copy

import numpy as np
from torch import nn

from sts.env.ironclad import CONTRACT, REGIONS, semantic_extensions
from sts.models.comparison import (
    CARD_KEYS, FEATURES, SLOTS, ComparisonActorCritic, encode as encode_comparison,
)

EXTRA_CARD_KEYS = {"combat_damage_bonus", "is_strike", "effective_exhaust", "cost_kind"}
EXTRA_FEATURES = 6
ENCODING_VERSION = "ironclad-set-encoding-v1"


def encode(obs):
    """严格消费新增字段；当前64容量只适用继承内容，不是全卡生成界。"""
    if obs.get("schema") != CONTRACT["observation_schema"]:
        raise ValueError("扩展编码schema不匹配")
    if obs.get("decision") != {"phase": "NORMAL", "selection": None}:
        raise ValueError("候选头尚未验收")
    base = copy.deepcopy(obs)
    del base["decision"]
    base["schema"] = "public-observation-v1"
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
    from sts.env.public_battle import _canonical
    ordered = copy.deepcopy(obs)
    for region in REGIONS[1:]:
        pairs = list(zip(base[region], ordered[region]))
        pairs.sort(key=lambda pair: _canonical(pair[0]))
        base[region] = [a for a, _ in pairs]
        ordered[region] = [b for _, b in pairs]
    result = encode_comparison(base)
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
        self.card_projection = nn.Sequential(nn.Linear(FEATURES + EXTRA_FEATURES + 8, 32), nn.Tanh())
        self.encoding_version = ENCODING_VERSION
