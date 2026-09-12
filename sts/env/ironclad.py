"""全卡扩展的独立开发入口；按里程碑验收，当前仅继承旧内容。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from sts.env.lightspeed import _load_backend
from sts.env.public_battle import PUBLIC_CONTRACT, PublicBattleEnv, _integer, normalize_observation

PATH = Path(__file__).with_name("ironclad-expansion-contract.json")
CONTRACT = json.loads(PATH.read_text(encoding="utf-8"))
CONTRACT_HASH = hashlib.sha256(PATH.read_bytes()).hexdigest()
REGISTRY_PATH = PATH.with_name("ironclad-registry.json")
REGISTRY = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
REGISTRY_HASH = hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest()
CARD_BY_NAME = {r["name"]: r for r in REGISTRY["cards"]}
RUNTIME_CONTRACT = {**PUBLIC_CONTRACT, "cards": REGISTRY["cards"], "observation_schema": CONTRACT["observation_schema"]}
REGIONS = ("hand", "draw_pile", "discard_pile", "exhaust_pile")


def normalize_ironclad(raw):
    """不推断未观测字段；选择阶段须待独立出口验收后才能接受。"""
    value = json.loads(json.dumps(raw, allow_nan=False))
    if value.get("schema") != CONTRACT["observation_schema"]:
        raise ValueError("扩展观测schema不匹配")
    if value.get("decision") != {"phase": "NORMAL", "selection": None}:
        raise ValueError("选择阶段尚未验收")
    # 复用旧字段的严格准入检查，同时保留所有扩展字段与逐实体排序。
    value = normalize_observation(value, contract=RUNTIME_CONTRACT)
    hp_loss = _integer(value["player"].get("combust_hp_loss"), "combust_hp_loss")
    if hp_loss < 0:
        raise ValueError("Combust失血量不能为负")
    for region in REGIONS:
        for card in value[region]:
            if _integer(card.get("combat_damage_bonus"), "combat_damage_bonus") < 0:
                raise ValueError("实例增伤不能为负")
            for key in ("is_strike", "effective_exhaust", "effective_cost_known"):
                if not isinstance(card.get(key), bool):
                    raise ValueError(f"{key}必须为布尔值")
            _integer(card.get("printed_cost"), "printed_cost")
            if _integer(card.get("effective_cost"), "effective_cost") < 0:
                raise ValueError("有效费用不能为负")
            if card["effective_cost_known"] != (region == "hand"):
                raise ValueError("非手牌即时费用可见性错误")
            if card.get("cost_scope") not in {"UNKNOWN", "COMBAT", "TURN", "POWER", "ONCE"}:
                raise ValueError("未知费用作用范围")
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
        if (getattr(module, "IRONCLAD_REGISTRY_SHA256", None) != REGISTRY_HASH or
                getattr(module, "IRONCLAD_CONTRACT_SHA256", None) != CONTRACT_HASH):
            raise RuntimeError("后端与扩展契约指纹不一致，请重新构建")
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
                             action_schema=CONTRACT["action_schema"], registry_version=REGISTRY["schema"],
                             registry_hash=REGISTRY_HASH, training_admitted=False)
        return obs


def semantic_extensions(obs):
    """命名增量数值，供后续Set编码接入；不含槽号、候选ID或随机状态。"""
    cards = []
    for region in REGIONS:
        for card in obs[region]:
            cards.append([card["combat_damage_bonus"] / 50, float(card["is_strike"]),
                          float(card["effective_exhaust"]),
                          *[float(card["cost_kind"] == kind) for kind in ("ENERGY", "X", "UNPLAYABLE")],
                          card["printed_cost"] / 4, card["effective_cost"] / 4, float(card["effective_cost_known"]),
                          *[float(card["cost_scope"] == scope) for scope in ("UNKNOWN", "COMBAT", "TURN", "POWER", "ONCE")]])
    return {"cards": np.asarray(cards, dtype=np.float32).reshape(-1, 14),
            "player": np.asarray([obs["player"]["combust_hp_loss"] / 10], dtype=np.float32)}
