"""公开对局派生战斗的独立适配器；旧minimal-v1协议不受影响。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from sts.env.lightspeed import _load_backend


CONTRACT_PATH = Path(__file__).with_name("public-battle-contract.json")
PUBLIC_CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
CONTRACT_HASH = hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()
CARD_BY_NAME = {entry["name"]: entry for entry in PUBLIC_CONTRACT["cards"]}
POTION_BY_NAME = {entry["name"]: entry for entry in PUBLIC_CONTRACT["potions"]}
RELIC_BY_NAME = {entry["name"]: entry for entry in PUBLIC_CONTRACT["relics"]}
ACTION_COUNT = PUBLIC_CONTRACT["action_count"]


def _integer(value: Any, label: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{label}必须为整数")
    return int(value)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _reject_hidden_fields(value: Any) -> None:
    forbidden = {"seed", "source_seed", "rng", "rng_state", "unique_id", "uniqueId", "move_history", "moveHistory", "future_intent"}
    if isinstance(value, dict):
        for key, item in value.items():
            if key in forbidden or key.endswith("_rng"):
                raise ValueError(f"规范观测包含隐藏字段：{key}")
            _reject_hidden_fields(item)
    elif isinstance(value, list):
        for item in value:
            _reject_hidden_fields(item)


def normalize_observation(raw: Mapping[str, Any]) -> dict[str, Any]:
    """复制并检查语义输出，映射项目ID；不丢失牌堆或状态。"""
    observation = json.loads(json.dumps(raw, allow_nan=False))
    if observation.get("schema") != PUBLIC_CONTRACT["observation_schema"]:
        raise ValueError("public观测schema不匹配")
    _reject_hidden_fields(observation)
    for key in ("hand", "draw_pile", "discard_pile", "exhaust_pile"):
        if not isinstance(observation.get(key), list):
            raise ValueError(f"观测缺少完整{key}")
        for card in observation[key]:
            definition = CARD_BY_NAME.get(card.get("name"))
            if definition is None:
                raise ValueError(f"后端返回未登记卡牌：{card.get('name')}")
            upgrade = _integer(card.get("upgrade_count"), "upgrade_count")
            if not 0 <= upgrade <= definition["max_upgrade"]:
                raise ValueError("后端返回不支持的升级版本")
            card["card_id"] = definition["id"]
            if key == "hand" and card.get("cost_known") is not True:
                raise ValueError("手牌费用必须可见")
            if key != "hand" and card.get("cost_known") is not False:
                raise ValueError("非手牌费用未完成可见性核验")
        if key != "hand":
            observation[key].sort(key=lambda card: _canonical(card))
    if len(observation["hand"]) > PUBLIC_CONTRACT["capacity"]["hand"]:
        raise ValueError("手牌容量越界")
    count = sum(len(observation[key]) for key in ("hand", "draw_pile", "discard_pile", "exhaust_pile"))
    if count > PUBLIC_CONTRACT["capacity"]["max_card_entities_bound"]:
        raise ValueError("完整卡实体超过已证明的采集预算上界")
    for key, capacity in (("enemies", "targets"), ("potions", "potions")):
        if not isinstance(observation.get(key), list) or len(observation[key]) != PUBLIC_CONTRACT["capacity"][capacity]:
            raise ValueError(f"{key}容量不匹配")
    for potion in observation["potions"]:
        if potion.get("present"):
            if potion.get("name") not in POTION_BY_NAME:
                raise ValueError("后端返回未登记药水")
            potion["potion_id"] = POTION_BY_NAME[potion["name"]]["id"]
        else:
            potion["potion_id"] = 0
    if not isinstance(observation.get("relics"), list):
        raise ValueError("观测缺少遗物")
    for relic in observation["relics"]:
        if relic.get("name") not in RELIC_BY_NAME:
            raise ValueError("后端返回未登记遗物")
        relic["relic_id"] = RELIC_BY_NAME[relic["name"]]["id"]
    player = observation.get("player")
    if not isinstance(player, dict) or not isinstance(player.get("statuses"), dict):
        raise ValueError("观测缺少玩家完整状态")
    hp, max_hp = _integer(player.get("hp"), "hp"), _integer(player.get("max_hp"), "max_hp")
    if max_hp <= 0 or not 0 <= hp <= max_hp:
        raise ValueError("玩家HP非法")
    mask = np.asarray(observation.get("action_mask"))
    if mask.dtype != np.bool_ or mask.shape != (ACTION_COUNT,):
        raise ValueError("public动作mask必须为66位布尔值")
    observation["action_mask"] = mask.copy()
    return observation


def load_scene_manifest(path: str | Path | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    target = Path(path) if path is not None else Path(__file__).parents[2] / "docs/m2-public-scene-manifest.json"
    raw = target.read_bytes()
    manifest = json.loads(raw)
    if manifest.get("schema") != "public-scene-manifest-v1":
        raise ValueError("场景清单schema不匹配")
    payload = {key: value for key, value in manifest.items() if key != "manifest_payload_sha256"}
    if hashlib.sha256(_canonical(payload)).hexdigest() != manifest.get("manifest_payload_sha256"):
        raise ValueError("场景清单整体哈希不匹配")
    if manifest.get("source_admission_policy") != PUBLIC_CONTRACT["source_admission_policy"]:
        raise ValueError("场景来源准入策略不匹配")
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("manifest缺少场景列表")
    selected = []
    groups: dict[str, str] = {}
    scene_ids: set[str] = set()
    for row in scenes:
        if row["scene_id"] in scene_ids:
            raise ValueError("manifest重复scene_id")
        scene_ids.add(row["scene_id"])
        group, split = row["group_id"], row["research_split"]
        if group in groups and groups[group] != split:
            raise ValueError("同源run跨数据划分")
        groups[group] = split
        if row.get("content_admission_status") != "accepted":
            continue
        candidate = row.get("candidate")
        if not isinstance(candidate, dict) or row.get("content_blockers"):
            raise ValueError("被标记接受的场景内容不完整")
        candidate_hash = hashlib.sha256(_canonical(candidate)).hexdigest()
        if row.get("candidate_sha256") != candidate_hash:
            raise ValueError("场景内容哈希不匹配")
        selected.append(row)
    return {"path": str(target.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "source_admission_policy": manifest["source_admission_policy"]}, selected


class PublicBattleEnv:
    """仅接受具名派生场景或显式机制诊断场景的新battle接口。"""

    def __init__(self, max_actions: int = 512, *, backend: Any = None) -> None:
        limit = _integer(max_actions, "max_actions")
        if not 1 <= limit <= PUBLIC_CONTRACT["capacity"]["max_actions"]:
            raise ValueError("外部动作预算必须在1..512")
        module = _load_backend() if backend is None else backend
        if not hasattr(module, "PublicBattleEnv"):
            raise RuntimeError("扩展缺少PublicBattleEnv；请先重建新增适配器")
        self._env = module.PublicBattleEnv(limit)
        self.max_actions = limit
        self._context: dict[str, Any] = {}
        self._finished = True

    _normalize_observation = staticmethod(normalize_observation)

    def reset(self, scene: Mapping[str, Any], seed: int, *, diagnostic: bool = False, purpose: str = "development") -> dict[str, Any]:
        environment_seed = _integer(seed, "environment_seed")
        if purpose not in {"development", "train", "evaluation"}:
            raise ValueError("未知seed用途")
        valid = 0 <= environment_seed < 1000 if purpose == "evaluation" else 100000 <= environment_seed < 2**64
        if not valid:
            raise ValueError("环境seed与用途范围不符")
        if diagnostic:
            candidate = dict(scene)
            source_context = {"scene_kind": "mechanism-diagnostic", "historical_exact": False}
        elif scene.get("source_admission_policy") == "real-deck-configured-battle-v1":
            from sts.env.real_deck import validate_configured_scene

            candidate, source_context = validate_configured_scene(scene, purpose)
            source_context.update(scene_kind="real-deck-configured", historical_exact=False)
        else:
            if scene.get("content_admission_status") != "accepted" or scene.get("content_blockers"):
                raise ValueError("必须提供完整内容准入的派生场景；机制夹具需显式diagnostic=True")
            candidate = dict(scene["candidate"])
            if hashlib.sha256(_canonical(candidate)).hexdigest() != scene.get("candidate_sha256"):
                raise ValueError("派生场景内容哈希不匹配")
            source_context = {key: scene.get(key) for key in ("scene_id", "group_id", "research_split", "source_path", "raw_sha256", "source_build", "source_seed")}
            source_context.update(scene_kind="public-derived", historical_exact=False, source_admission_policy=PUBLIC_CONTRACT["source_admission_policy"])
        # 来源元数据仅进入info；不给C++观测，更不给策略编码。
        runtime_keys = ("entry_timing", "initialization_phase", "floor", "act", "character", "ascension", "player", "deck", "relics", "potions", "encounter", "burning_elite")
        if any(key not in candidate for key in runtime_keys[:-1]):
            raise ValueError("场景缺少必填入场字段")
        if _integer(candidate["act"], "act") != 1 or candidate["character"] != "IRONCLAD":
            raise ValueError("只支持Ironclad第一幕入口")
        payload = {key: candidate[key] for key in runtime_keys if key in candidate}
        self._finished = True
        observation = self._normalize_observation(json.loads(self._env.reset_scene(json.dumps(payload, allow_nan=False), environment_seed)))
        self._context = {**source_context, "environment_seed": environment_seed, "seed_purpose": purpose,
                         "contract_id": PUBLIC_CONTRACT["contract_id"], "contract_hash": CONTRACT_HASH,
                         "reward_version": PUBLIC_CONTRACT["reward_version"], "gamma": 1.0,
                         "task_type": "battle", "task_spec_id": PUBLIC_CONTRACT["contract_id"],
                         "environment_version": PUBLIC_CONTRACT["contract_id"], "alpha_hp": 0.5, "beta": 0.0,
                         "observation_schema": PUBLIC_CONTRACT["observation_schema"],
                         "registry_version": PUBLIC_CONTRACT["registry_version"], "action_schema_version": PUBLIC_CONTRACT["action_schema_version"],
                         "termination_rule_version": PUBLIC_CONTRACT["termination_rule_version"], "max_actions": self.max_actions}
        self._finished = False
        return observation

    def step(self, action: int):
        selected = _integer(action, "action")
        if self._finished:
            raise RuntimeError("必须先reset，终局后不能继续step")
        if not 0 <= selected < ACTION_COUNT:
            raise ValueError("动作必须在0..65")
        result = json.loads(self._env.step(selected))
        observation = self._normalize_observation(result["observation"])
        terminated, truncated = result["terminated"], result["truncated"]
        if not isinstance(terminated, bool) or not isinstance(truncated, bool) or terminated and truncated:
            raise ValueError("终止/截断字段非法")
        reward = float(result["reward"])
        if not np.isfinite(reward) or reward < 0 or reward > 1.5 or (not terminated and reward != 0):
            raise ValueError("battle_reward_v1返回值非法")
        self._finished = terminated or truncated
        info = {**result.get("info", {}), **self._context, "reward_base": reward, "reward_train": reward,
                "task_outcome": "victory" if reward > 0 else "defeat" if terminated else "ongoing",
                "termination_reason": "victory" if reward > 0 else "defeat" if terminated else "external_action_budget" if truncated else "ongoing"}
        return observation, reward, terminated, truncated, info

    def observation(self) -> dict[str, Any]:
        return self._normalize_observation(json.loads(self._env.observation()))

    def action_mask(self) -> np.ndarray:
        mask = np.asarray(self._env.action_mask())
        if mask.shape != (ACTION_COUNT,) or mask.dtype != np.bool_:
            raise ValueError("后端mask协议不匹配")
        return mask.copy()
