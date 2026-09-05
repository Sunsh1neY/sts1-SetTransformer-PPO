"""正式 lightspeed 战斗后端的稳定 Python 薄包装。"""

from __future__ import annotations

import importlib
import sys
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, TypedDict

import numpy as np
from numpy.typing import NDArray


HAND_FEATURES = ("card_id", "upgraded", "cost")
PILE_FEATURES = ("bash_count", "defend_count", "strike_count")
ENEMY_FEATURES = (
    "monster_id",
    "hp",
    "max_hp",
    "block",
    "strength",
    "vulnerable",
    "weak",
    "intent",
    "intent_damage",
    "intent_hits",
    "curl_up",
    "ritual",
)
GLOBAL_FEATURES = (
    "hp",
    "max_hp",
    "block",
    "energy",
    "turn",
    "draw_count",
    "discard_count",
    "total_enemy_hp",
    "strength",
    "vulnerable",
    "weak",
)

MAX_HAND = 10
MAX_ENEMIES = 5
ACTION_COUNT = 31


Observation = TypedDict(
    "Observation",
    {
        "hand": NDArray[np.int32],
        "enemies": NDArray[np.int32],
        "draw_pile": NDArray[np.int32],
        "discard_pile": NDArray[np.int32],
        "global": NDArray[np.int32],
        "hand_mask": NDArray[np.bool_],
        "enemy_mask": NDArray[np.bool_],
        "action_mask": NDArray[np.bool_],
    },
)


class Encounter(str, Enum):
    """当前最小切片允许的遭遇。"""

    JAW_WORM = "jaw-worm"
    CULTIST = "cultist"
    TWO_LOUSE = "two-louse"


def _load_backend() -> ModuleType:
    """优先导入已安装扩展，本地开发时回退到锁定源码的构建目录。"""

    try:
        return importlib.import_module("slaythespire")
    except ModuleNotFoundError as exc:
        if exc.name != "slaythespire":
            raise

    build_dir = Path(__file__).parents[2] / "third_party" / "sts_lightspeed" / "build"
    if not build_dir.is_dir():
        raise ImportError(
            "找不到 slaythespire 扩展；请先运行 scripts/build-lightspeed.ps1"
        ) from None

    build_path = str(build_dir)
    sys.path.insert(0, build_path)
    try:
        return importlib.import_module("slaythespire")
    except ImportError as exc:
        raise ImportError(
            f"无法从 {build_dir} 导入 slaythespire；请重新构建与当前 Python 匹配的扩展"
        ) from exc
    finally:
        if sys.path[0] == build_path:
            sys.path.pop(0)


def _check_backend_layout(backend: ModuleType) -> None:
    actual = {
        "HAND_FEATURES": tuple(backend.HAND_FEATURES),
        "ENEMY_FEATURES": tuple(backend.ENEMY_FEATURES),
        "PILE_FEATURES": tuple(backend.PILE_FEATURES),
        "GLOBAL_FEATURES": tuple(backend.GLOBAL_FEATURES),
    }
    expected = {
        "HAND_FEATURES": HAND_FEATURES,
        "ENEMY_FEATURES": ENEMY_FEATURES,
        "PILE_FEATURES": PILE_FEATURES,
        "GLOBAL_FEATURES": GLOBAL_FEATURES,
    }
    for name, expected_fields in expected.items():
        if actual[name] != expected_fields:
            raise RuntimeError(
                f"C++ 观测字段 {name} 已漂移：期望 {expected_fields}，实际 {actual[name]}"
            )


def _reshape_int(values: Any, shape: tuple[int, ...], name: str) -> NDArray[np.int32]:
    result = np.asarray(values, dtype=np.int32)
    expected_size = int(np.prod(shape))
    if result.size != expected_size:
        raise ValueError(f"{name} 长度应为 {expected_size}，实际为 {result.size}")
    return result.reshape(shape).copy()


def _reshape_mask(values: Any, size: int, name: str) -> NDArray[np.bool_]:
    result = np.asarray(values, dtype=np.bool_)
    if result.size != size:
        raise ValueError(f"{name} 长度应为 {size}，实际为 {result.size}")
    return result.reshape(size).copy()


def _observation_to_dict(observation: Any) -> Observation:
    """白名单转换，并清除上游无效实体行可能携带的残留值。"""

    hand = _reshape_int(observation.hand, (MAX_HAND, len(HAND_FEATURES)), "hand")
    enemies = _reshape_int(
        observation.enemies,
        (MAX_ENEMIES, len(ENEMY_FEATURES)),
        "enemies",
    )
    global_values = _reshape_int(
        getattr(observation, "global"),
        (len(GLOBAL_FEATURES),),
        "global",
    )
    draw_pile = _reshape_int(
        observation.draw_pile,
        (len(PILE_FEATURES),),
        "draw_pile",
    )
    discard_pile = _reshape_int(
        observation.discard_pile,
        (len(PILE_FEATURES),),
        "discard_pile",
    )
    hand_mask = _reshape_mask(observation.hand_mask, MAX_HAND, "hand_mask")
    enemy_mask = _reshape_mask(observation.enemy_mask, MAX_ENEMIES, "enemy_mask")
    action_mask = _reshape_mask(observation.action_mask, ACTION_COUNT, "action_mask")

    hand[~hand_mask] = 0
    enemies[~enemy_mask] = 0
    return {
        "hand": hand,
        "enemies": enemies,
        "draw_pile": draw_pile,
        "discard_pile": discard_pile,
        "global": global_values,
        "hand_mask": hand_mask,
        "enemy_mask": enemy_mask,
        "action_mask": action_mask,
    }


class LightspeedBattleEnv:
    """将 C++ BattleObservation 转为稳定、独立的规范观测 dict。"""

    def __init__(self, max_turns: int = 50, gamma: float = 1.0) -> None:
        self._backend = _load_backend()
        _check_backend_layout(self._backend)
        self._env = self._backend.IroncladBattleEnv(
            max_turns=max_turns,
            gamma=gamma,
        )

    @property
    def max_turns(self) -> int:
        return int(self._env.max_turns)

    @property
    def gamma(self) -> float:
        return float(self._env.gamma)

    def _backend_encounter(self, encounter: Encounter | str) -> Any:
        try:
            normalized = Encounter(encounter)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in Encounter)
            raise ValueError(f"未知遭遇 {encounter!r}；可用值：{allowed}") from exc
        names = {
            Encounter.JAW_WORM: "JAW_WORM",
            Encounter.CULTIST: "CULTIST",
            Encounter.TWO_LOUSE: "TWO_LOUSE",
        }
        return getattr(self._backend.MonsterEncounter, names[normalized])

    def reset(
        self,
        seed: int,
        encounter: Encounter | str,
        ascension: int = 0,
    ) -> Observation:
        raw = self._env.reset(
            int(seed),
            self._backend_encounter(encounter),
            int(ascension),
        )
        return _observation_to_dict(raw)

    def step(
        self,
        action: int,
    ) -> tuple[Observation, float, bool, bool, dict[str, int]]:
        result = self._env.step(int(action))
        observation = _observation_to_dict(result.observation)
        info = {str(key): int(value) for key, value in result.info.items()}
        return (
            observation,
            float(result.reward),
            bool(result.terminated),
            bool(result.truncated),
            info,
        )

    def observation(self) -> Observation:
        return _observation_to_dict(self._env.observation())

    def action_mask(self) -> NDArray[np.bool_]:
        return _reshape_mask(self._env.action_mask(), ACTION_COUNT, "action_mask")
