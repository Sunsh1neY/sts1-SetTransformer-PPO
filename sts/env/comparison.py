"""固定MLP/Set任务的容量采集边界；不丢实体或伪造失败。"""
import hashlib
import json
from pathlib import Path

from sts.env.public_battle import CONTRACT_HASH, PublicBattleEnv, _canonical
from sts.env.real_deck import load_batch

PATH = Path(__file__).with_name("comparison-contract.json")


def load_contract():
    value = json.loads(PATH.read_text(encoding="utf-8"))
    payload = {k: v for k, v in value.items() if k != "payload_sha256"}
    if hashlib.sha256(_canonical(payload)).hexdigest() != value["payload_sha256"]:
        raise ValueError("对照契约哈希不匹配")
    if value["batch_sha256"] != load_batch()["payload_sha256"] or value["public_contract_sha256"] != CONTRACT_HASH:
        raise ValueError("对照环境已改变，需要新版本")
    if value["truncate_at"] - 1 + value["generated_per_action"] > value["card_entities"]:
        raise ValueError("未预留生成余量")
    return value


def card_count(obs):
    return sum(len(obs[k]) for k in ("hand", "draw_pile", "discard_pile", "exhaust_pile"))


class ComparisonEnv:
    def __init__(self):
        self.contract = load_contract()
        self.env = PublicBattleEnv(max_actions=self.contract["max_actions"])
        self.finished = True

    def reset(self, scene, seed, purpose="development"):
        if len(scene["candidate"]["deck"]) > self.contract["initial_cards"]:
            raise ValueError("初始卡组超出冻结范围")
        obs = self.env.reset(scene, seed, purpose=purpose)
        self.count = card_count(obs)
        self.finished = False
        return obs

    def step(self, action):
        if self.finished:
            raise RuntimeError("采集已结束，必须reset")
        obs, reward, terminated, truncated, info = self.env.step(action)
        count = card_count(obs)
        if count > self.count + self.contract["generated_per_action"] or count > self.contract["card_entities"]:
            self.finished = True
            raise RuntimeError("生成量超出已证明边界，拒绝残缺轨迹")
        self.count = count
        if not terminated and count >= self.contract["truncate_at"]:
            truncated = True
            info["termination_reason"] = "external_card_capacity"
            info["truncation_reason"] = "external_card_capacity"
        self.finished = terminated or truncated
        info.update(comparison_contract_sha256=self.contract["payload_sha256"],
                    environment_version=self.contract["schema"], task_spec_id=self.contract["schema"],
                    termination_rule_version=self.contract["termination_rule_version"], card_entities=count)
        return obs, reward, terminated, truncated, info
