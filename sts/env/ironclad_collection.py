"""独立扩展的完整决策点容量截断；资源计数只进info。"""
import hashlib
import json
from pathlib import Path

from sts.env.ironclad import CONTRACT_HASH, REGISTRY_HASH, REGIONS, IroncladEnv

PATH = Path(__file__).with_name("ironclad-capacity.json")


def load_capacity(path=None):
    raw = (PATH if path is None else path).read_bytes()
    value = json.loads(raw)
    if value["registry_sha256"] != REGISTRY_HASH or value["runtime_contract_sha256"] != CONTRACT_HASH:
        raise ValueError("内容或运行契约改变，必须重新证明容量边界")
    if value["initial_cards"] >= value["truncate_at"]:
        raise ValueError("初始容量未保留动作余量")
    if value["truncate_at"] - 1 + value["generated_per_decision"] > value["card_entities"]:
        raise ValueError("容量阈值未预留完整原子动作余量")
    if value["max_allocated_entities"] != value["initial_cards"] + value["max_actions"] * value["generated_per_decision"]:
        raise ValueError("累计分配预算不一致")
    if value["max_allocated_entities"] >= 32767:
        raise ValueError("累计分配可能溢出后端int16")
    return {**value, "sha256": hashlib.sha256(raw).hexdigest()}


def card_count(obs):
    return sum(len(obs[zone]) for zone in REGIONS)


class IroncladCollectionEnv:
    """仅开发采集；未完成正式批次准入和PPO版本绑定。"""

    load_contract = staticmethod(load_capacity)

    def __init__(self, max_actions=512):
        self.contract = self.load_contract()
        self.env = IroncladEnv(max_actions=max_actions)
        if not hasattr(self.env._env, "allocated_card_count"):
            raise RuntimeError("后端缺少累计分配计数，请重建")
        self.finished = True

    def reset(self, scene, seed, *, diagnostic=False, purpose="development"):
        self.finished = True
        if not 1 <= len(scene.get("deck", [])) <= self.contract["initial_cards"]:
            raise ValueError(f"采集初始卡组必须完整且不超过{self.contract['initial_cards']}张")
        obs = self.env.reset(scene, seed, diagnostic=diagnostic, purpose=purpose)
        self.count = card_count(obs)
        self.allocated = self.env._env.allocated_card_count()
        if self.count > self.contract["initial_cards"] or self.allocated != len(scene["deck"]):
            raise RuntimeError("开战生成超出当前容量证明，拒绝采集")
        self.counters = {"decision_steps": 0, "card_plays": 0, "end_turns": 0, "potion_uses": 0, "selections": 0}
        self.finished = False
        return obs

    def step(self, action):
        if self.finished:
            raise RuntimeError("采集已结束或异常，必须reset")
        try:
            obs, reward, terminated, truncated, info = self.env.step(action)
            count = card_count(obs)
            allocated = self.env._env.allocated_card_count()
            growth = allocated - self.allocated
            if not 0 <= growth <= self.contract["generated_per_decision"]:
                raise RuntimeError("实际累计ID增长超出证明，轨迹异常")
            if count > self.contract["card_entities"] or allocated > self.contract["max_allocated_entities"]:
                raise RuntimeError("完整最终状态超出已证明容量，轨迹异常")
            reasons = [info["truncation_reason"]] if truncated else []
            if not terminated and count >= self.contract["truncate_at"]:
                truncated = True
                reasons.append("external_card_capacity")
                info.update(termination_reason="external_card_capacity", truncation_reason="external_card_capacity")
            self.count, self.allocated = count, allocated
            self.counters["decision_steps"] += 1
            self.counters["selections" if isinstance(action, dict) else "card_plays" if action < 50 else "end_turns" if action == 50 else "potion_uses"] += 1
            info.update(self.counters)
            info.update(card_entities=count, allocated_card_entities=allocated, generated_card_entities=growth,
                        collection_contract_hash=self.contract["sha256"], collection_version=self.contract["schema"],
                        termination_rule_version=self.contract["termination_rule_version"], truncation_reasons=reasons)
            self.finished = terminated or truncated
            return obs, reward, terminated, truncated, info
        except Exception:
            # 发生部分推进或校验错误后不继续消费同一轨迹。
            self.finished = True
            raise
