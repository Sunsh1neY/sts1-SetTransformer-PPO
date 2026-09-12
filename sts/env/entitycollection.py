"""统一实体主线的资源采集边界；不沿用MLP对照的64张模型限制。"""
import hashlib
from pathlib import Path

from sts.env.entities import CONTRACT_HASH, encode_observation
from sts.env.ironclad_collection import IroncladCollectionEnv, load_capacity
from sts.env.lightspeed import _load_backend

PATH = Path(__file__).with_name("unified-entity-capacity.json")


def load_entity_capacity():
    contract = load_capacity(PATH)
    if contract["entity_contract_sha256"] != CONTRACT_HASH:
        raise ValueError("统一实体词表/资源配置已改变，需要重审采集边界")
    backend_hash = hashlib.sha256(Path(_load_backend().__file__).read_bytes()).hexdigest()
    if contract["backend_sha256"] != backend_hash:
        raise ValueError("后端实现已改变，需要重新核验生成与资源边界")
    return contract


class UnifiedEntityCollectionEnv(IroncladCollectionEnv):
    load_contract = staticmethod(load_entity_capacity)

    def reset(self, *args, **kwargs):
        try:
            obs = super().reset(*args, **kwargs)
            encode_observation(obs)
            return obs
        except Exception:
            self.finished = True
            raise

    def step(self, action):
        try:
            result = super().step(action)
            encode_observation(result[0])
            return result
        except Exception:
            self.finished = True
            raise
