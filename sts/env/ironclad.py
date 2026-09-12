"""全卡扩展的独立开发入口；按里程碑验收，当前仅继承旧内容。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from sts.env.lightspeed import _load_backend
from sts.env.public_battle import PublicBattleEnv, _integer, normalize_observation

PATH = Path(__file__).with_name("ironclad-expansion-contract.json")
CONTRACT = json.loads(PATH.read_text(encoding="utf-8"))
CONTRACT_HASH = hashlib.sha256(PATH.read_bytes()).hexdigest()
REGIONS = ("hand", "draw_pile", "discard_pile", "exhaust_pile")


def normalize_ironclad(raw):
    """不推断未观测字段；选择阶段须待独立出口验收后才能接受。"""
    value = json.loads(json.dumps(raw, allow_nan=False))
    if value.get("schema") != CONTRACT["observation_schema"]:
        raise ValueError("扩展观测schema不匹配")
    if value.get("decision") != {"phase": "NORMAL", "selection": None}:
        raise ValueError("选择阶段尚未验收")
    # 复用旧字段的严格准入检查，同时保留所有扩展字段与逐实体排序。
    value["schema"] = "public-observation-v1"
    value = normalize_observation(value)
    value["schema"] = CONTRACT["observation_schema"]
    hp_loss = _integer(value["player"].get("combust_hp_loss"), "combust_hp_loss")
    if hp_loss < 0:
        raise ValueError("Combust失血量不能为负")
    for region in REGIONS:
        for card in value[region]:
            if _integer(card.get("combat_damage_bonus"), "combat_damage_bonus") < 0:
                raise ValueError("实例增伤不能为负")
            for key in ("is_strike", "effective_exhaust"):
                if not isinstance(card.get(key), bool):
                    raise ValueError(f"{key}必须为布尔值")
            if card.get("cost_kind") not in {"ENERGY", "X", "UNPLAYABLE"}:
                raise ValueError("未知费用类别")
    return value


class IroncladEnv(PublicBattleEnv):
    """仅允许显式机制夹具；当前不批准正式扩展训练或旧数据自动迁移。"""

    _normalize_observation = staticmethod(normalize_ironclad)

    def __init__(self, max_actions=512):
        module = _load_backend()
        if not hasattr(module, "IroncladExpandedBattleEnv"):
            raise RuntimeError("请先用独立扩展构建脚本编译后端")
        super().__init__(max_actions, backend=SimpleNamespace(PublicBattleEnv=module.IroncladExpandedBattleEnv))

    def reset(self, scene, seed, *, diagnostic=False, purpose="development"):
        if not diagnostic or purpose != "development":
            raise ValueError("当前扩展仅批准development机制夹具，正式采集尚未开放")
        if _integer(scene.get("ascension"), "ascension") != CONTRACT["scope"]["ascension"]:
            raise ValueError("扩展范围限定A20")
        if scene.get("encounter") not in CONTRACT["scope"]["encounters"]:
            raise ValueError("遭遇不在扩展范围")
        obs = super().reset(scene, seed, diagnostic=True, purpose=purpose)
        self._context.update(contract_id=CONTRACT["schema"], contract_hash=CONTRACT_HASH,
                             task_spec_id=CONTRACT["schema"], environment_version=CONTRACT["schema"],
                             observation_schema=CONTRACT["observation_schema"],
                             action_schema=CONTRACT["action_schema"], training_admitted=False)
        return obs


def semantic_extensions(obs):
    """命名增量数值，供后续Set编码接入；不含槽号、候选ID或随机状态。"""
    cards = []
    for region in REGIONS:
        for card in obs[region]:
            cards.append([card["combat_damage_bonus"] / 50, float(card["is_strike"]),
                          float(card["effective_exhaust"]),
                          *[float(card["cost_kind"] == kind) for kind in ("ENERGY", "X", "UNPLAYABLE")]])
    return {"cards": np.asarray(cards, dtype=np.float32).reshape(-1, 6),
            "player": np.asarray([obs["player"]["combust_hp_loss"] / 10], dtype=np.float32)}
