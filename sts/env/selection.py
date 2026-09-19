"""单选候选的公开视图与一次性路由；尚未接入战斗step。"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import json
import uuid

from sts.env.public_battle import _integer

# 白名单避免后端位置、内部状态或未来随机信息混入候选token。
CARD_FIELDS = frozenset({
    "name", "card_id", "upgrade_count", "cost", "cost_known", "base_cost", "target_kind",
    "damage", "block", "base_block", "magic", "hits", "damage_by_target", "all_enemies",
    "card_type", "exhaust", "ethereal", "free_to_play_once", "retain", "combat_damage_bonus",
    "is_strike", "cost_kind", "effective_exhaust", "printed_cost", "effective_cost",
    "effective_cost_known", "cost_scope",
})
ZONES = {
    "ARMAMENTS": "hand", "DUAL_WIELD": "hand", "EXHAUST_ONE": "hand",
    "EXHUME": "exhaust_pile", "HEADBUTT": "discard_pile", "WARCRY": "hand", "DISCOVERY": "offer",
}


@dataclass(frozen=True)
class SelectionTarget:
    """内部结果，仅供适配器构造后端SINGLE_CARD_SELECT，不用于模型编码。"""

    kind: str
    zone: str
    backend_index: int


class SelectionRouter:
    """发布已由后端筛选的合法候选；本组件不猜测合法性或自动代选。"""

    def __init__(self, capacity=4096):
        self.capacity = _integer(capacity, "候选容量")
        if not 1 <= self.capacity <= 65536:
            raise ValueError("候选容量超出单选路由索引范围")
        # 与游戏/策略RNG独立。路由凭据不进入语义视图，也不用于学习。
        self._session = uuid.uuid4().hex
        self._sequence = 0
        self.invalidate()

    def invalidate(self):
        """reset、失败或接受动作后必须使旧候选失效。"""
        self._token = None
        self._view = None
        self._targets = ()

    def publish(self, kind, candidates):
        """candidates是(后端牌区索引,已规范化卡牌记录)的完整合法候选序列。"""
        # 即使发布失败，也不能回退消费上一次决策。
        self.invalidate()
        if kind not in ZONES:
            raise ValueError("未支持的单选任务")
        pairs = list(candidates)
        if not 1 <= len(pairs) <= self.capacity:
            raise ValueError("候选为空或超过容量；不能截掉候选")
        copied, indices = [], set()
        for raw_index, card in pairs:
            index = _integer(raw_index, "后端牌区索引")
            if not 0 <= index <= 65535 or index in indices:
                raise ValueError("后端牌区索引越界或重复")
            if ZONES[kind] == "hand" and index >= 10:
                raise ValueError("后端手牌索引越界")
            indices.add(index)
            if not isinstance(card, dict) or set(card) != CARD_FIELDS | ({"known_top", "recovery_cost", "draw_position_known", "draw_position"} & set(card)):
                raise ValueError("候选必须使用完整规范语义，不能包含路由或隐藏字段")
            # JSON复制还会拒绝NaN与不可序列化内部对象。
            row = json.loads(json.dumps(card, ensure_ascii=False, allow_nan=False))
            copied.append((index, row))
        if ZONES[kind] != "hand":
            copied.sort(key=lambda pair: json.dumps(pair[1], sort_keys=True, ensure_ascii=False, separators=(",", ":")))
        self._sequence += 1
        self._token = f"{self._session}:{self._sequence}"
        self._targets = tuple(SelectionTarget(kind, ZONES[kind], index) for index, _ in copied)
        self._view = {"phase": "SELECT_CARD", "selection_kind": kind,
                      "candidate_zone": ZONES[kind], "min_choices": 1, "max_choices": 1,
                      "candidates": [row for _, row in copied], "candidate_mask": [True] * len(copied)}
        return self.snapshot()

    def snapshot(self):
        if self._token is None:
            raise RuntimeError("没有有效选牌决策")
        # 只有semantic允许进入编码器；routing用于回送动作。
        return {"semantic": copy.deepcopy(self._view), "routing": {"decision_id": self._token}}

    def take(self, action):
        """解析一次性选择；适配器取得目标后执行后端，失败也不得复用凭据。"""
        if self._token is None:
            raise RuntimeError("选牌决策已失效")
        if not isinstance(action, dict) or set(action) != {"kind", "decision_id", "candidate_index"}:
            raise ValueError("单选动作字段不匹配")
        if action["kind"] != "SELECT_CARD" or action["decision_id"] != self._token:
            raise ValueError("过期或其他环境的选牌引用")
        index = _integer(action["candidate_index"], "公开候选位置")
        if not 0 <= index < len(self._targets):
            raise ValueError("公开候选位置越界")
        target = self._targets[index]
        self.invalidate()
        return target
