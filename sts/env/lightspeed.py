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

from sts.env.registry import (
    DEFAULT_CARD_REGISTRY,
    SCHEMA_VERSION,
    CardLocation,
    CardRegistry,
)

CARD_FEATURES = ("backend_card_id", "location", "upgraded", "cost", "cost_known")
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
    "hand_count",
    "draw_count",
    "discard_count",
    "exhaust_count",
    "total_enemy_hp",
    "strength",
    "vulnerable",
    "weak",
)

MAX_HAND = 10
MAX_ENEMIES = 5
ACTION_COUNT = 31


class CardObservation(TypedDict):
    """一张玩家可见卡牌的 V2 规范记录。"""

    card_id: int
    location: int
    upgraded: bool
    cost: int
    cost_known: bool
    target_kind: int


Observation = TypedDict(
    "Observation",
    {
        "hand": list[CardObservation],
        "enemies": NDArray[np.int32],
        "draw_pile": list[CardObservation],
        "discard_pile": list[CardObservation],
        "exhaust_pile": list[CardObservation],
        "global": NDArray[np.int32],
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
        "CARD_FEATURES": tuple(backend.CARD_FEATURES),
        "ENEMY_FEATURES": tuple(backend.ENEMY_FEATURES),
        "GLOBAL_FEATURES": tuple(backend.GLOBAL_FEATURES),
    }
    expected = {
        "CARD_FEATURES": CARD_FEATURES,
        "ENEMY_FEATURES": ENEMY_FEATURES,
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


def _card_rows(values: Any, name: str, row_count: int | None = None) -> NDArray[np.int32]:
    result = np.asarray(values, dtype=np.int32)
    width = len(CARD_FEATURES)
    if row_count is None:
        if result.size % width != 0:
            raise ValueError(f"{name} 长度必须是 CARD_FEATURES={width} 的整数倍")
        row_count = result.size // width
    expected_size = row_count * width
    if result.size != expected_size:
        raise ValueError(f"{name} 长度应为 {expected_size}，实际为 {result.size}")
    return result.reshape(row_count, width).copy()


def _card_record(
    row: NDArray[np.int32],
    *,
    expected_location: CardLocation,
    registry: CardRegistry,
    name: str,
) -> CardObservation:
    location = int(row[1])
    upgraded = int(row[2])
    cost_known = int(row[4])
    if location != int(expected_location):
        raise ValueError(
            f"{name} location 应为 {int(expected_location)}，实际为 {location}"
        )
    if upgraded not in (0, 1) or cost_known not in (0, 1):
        raise ValueError(f"{name} 的 upgraded/cost_known 必须为 0 或 1")
    if expected_location == CardLocation.HAND and cost_known != 1:
        raise ValueError(f"{name} 手牌费用必须标记为已知")
    if expected_location != CardLocation.HAND and cost_known != 0:
        raise ValueError(f"{name} 非手牌费用尚未核验，必须标记为未知")
    definition = registry.from_backend_id(int(row[0]))
    return {
        "card_id": definition.registry_id,
        "location": location,
        "upgraded": bool(upgraded),
        "cost": int(row[3]) if cost_known else 0,
        "cost_known": bool(cost_known),
        "target_kind": int(definition.target_kind),
    }


def _pile_records(
    values: Any,
    *,
    location: CardLocation,
    registry: CardRegistry,
    name: str,
) -> list[CardObservation]:
    records = [
        _card_record(
            row,
            expected_location=location,
            registry=registry,
            name=f"{name}[{index}]",
        )
        for index, row in enumerate(_card_rows(values, name))
    ]
    return sorted(
        records,
        key=lambda card: (
            card["card_id"],
            card["upgraded"],
            card["cost_known"],
            card["cost"],
            card["target_kind"],
        ),
    )


def _observation_to_dict(
    observation: Any,
    registry: CardRegistry = DEFAULT_CARD_REGISTRY,
) -> Observation:
    """白名单转换，并清除上游无效实体行可能携带的残留值。"""

    raw_hand = _card_rows(observation.hand, "hand", MAX_HAND)
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
    hand_mask = _reshape_mask(observation.hand_mask, MAX_HAND, "hand_mask")
    enemy_mask = _reshape_mask(observation.enemy_mask, MAX_ENEMIES, "enemy_mask")
    action_mask = _reshape_mask(observation.action_mask, ACTION_COUNT, "action_mask")

    hand = [
        _card_record(
            raw_hand[index],
            expected_location=CardLocation.HAND,
            registry=registry,
            name=f"hand[{index}]",
        )
        for index in np.flatnonzero(hand_mask)
    ]
    draw_pile = _pile_records(
        observation.draw_pile,
        location=CardLocation.DRAW,
        registry=registry,
        name="draw_pile",
    )
    discard_pile = _pile_records(
        observation.discard_pile,
        location=CardLocation.DISCARD,
        registry=registry,
        name="discard_pile",
    )
    exhaust_pile = _pile_records(
        observation.exhaust_pile,
        location=CardLocation.EXHAUST,
        registry=registry,
        name="exhaust_pile",
    )
    enemies[~enemy_mask] = 0
    expected_counts = (
        len(hand),
        len(draw_pile),
        len(discard_pile),
        len(exhaust_pile),
    )
    actual_counts = tuple(map(int, global_values[5:9]))
    if actual_counts != expected_counts:
        raise RuntimeError(
            f"四区卡牌数量与 global 不一致：记录={expected_counts}，global={actual_counts}"
        )
    return {
        "hand": hand,
        "enemies": enemies,
        "draw_pile": draw_pile,
        "discard_pile": discard_pile,
        "exhaust_pile": exhaust_pile,
        "global": global_values,
        "enemy_mask": enemy_mask,
        "action_mask": action_mask,
    }


class LightspeedBattleEnv:
    """将 C++ BattleObservation 转为稳定、独立的规范观测 dict。"""

    def __init__(
        self,
        max_turns: int = 50,
        gamma: float = 1.0,
        registry: CardRegistry = DEFAULT_CARD_REGISTRY,
    ) -> None:
        self._backend = _load_backend()
        _check_backend_layout(self._backend)
        self.registry = registry
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

    @property
    def schema_version(self) -> int:
        return SCHEMA_VERSION

    @property
    def registry_version(self) -> int:
        return self.registry.version

    @property
    def registry_hash(self) -> str:
        return self.registry.content_hash

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
        return _observation_to_dict(raw, self.registry)

    def step(
        self,
        action: int,
    ) -> tuple[Observation, float, bool, bool, dict[str, int]]:
        result = self._env.step(int(action))
        observation = _observation_to_dict(result.observation, self.registry)
        info = {str(key): int(value) for key, value in result.info.items()}
        return (
            observation,
            float(result.reward),
            bool(result.terminated),
            bool(result.truncated),
            info,
        )

    def observation(self) -> Observation:
        return _observation_to_dict(self._env.observation(), self.registry)

    def action_mask(self) -> NDArray[np.bool_]:
        return _reshape_mask(self._env.action_mask(), ACTION_COUNT, "action_mask")
