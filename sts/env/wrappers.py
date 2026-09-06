"""把 V2 规范观测确定性整理为 MLP 与 Set Transformer 的同源输入。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, TypedDict

import numpy as np
from numpy.typing import NDArray

from sts.env.lightspeed import (
    ACTION_COUNT,
    ENEMY_FEATURES,
    GLOBAL_FEATURES,
    MAX_ENEMIES,
    MAX_HAND,
    CardObservation,
    LightspeedBattleEnv,
)
from sts.env.registry import CardLocation, CardRegistry, PAD_ID


# 固定容量属于输入 schema；扩容时必须显式改版本并重新检查模型兼容性。
PILE_CAPACITY = 10
CARD_CAPACITY = MAX_HAND + PILE_CAPACITY
CARD_CATEGORICAL_FEATURES = ("card_id", "location", "target_kind", "upgraded")
CARD_NUMERIC_FEATURES = ("cost",)

# 敌人暂沿用 V1 的公开编码。类别先转 one-hot，不能把 ID 当连续大小。
MONSTER_CATEGORIES = (14, 23, 28, 37)  # Cultist、Green Louse、Jaw Worm、Red Louse
INTENT_CATEGORIES = (0, 1, 2, 3, 4, 5)
MONSTER_TO_INDEX = {value: index for index, value in enumerate(MONSTER_CATEGORIES)}
INTENT_TO_INDEX = {value: index for index, value in enumerate(INTENT_CATEGORIES)}

ENEMY_ENCODED_FEATURES = (
    "monster_is_cultist",
    "monster_is_green_louse",
    "monster_is_jaw_worm",
    "monster_is_red_louse",
    "hp",
    "max_hp",
    "block",
    "strength",
    "vulnerable",
    "weak",
    "intent_is_none",
    "intent_is_attack",
    "intent_is_attack_defend",
    "intent_is_defend_buff",
    "intent_is_buff",
    "intent_is_debuff",
    "intent_damage",
    "intent_hits",
    "curl_up",
    "ritual",
)

CARD_CATEGORICAL_DIM = len(CARD_CATEGORICAL_FEATURES)
CARD_NUMERIC_DIM = len(CARD_NUMERIC_FEATURES)
ENEMY_ENCODED_DIM = len(ENEMY_ENCODED_FEATURES)
GLOBAL_ENCODED_DIM = len(GLOBAL_FEATURES)

_FLAT_SIZES = (
    ("card_categorical", CARD_CAPACITY * CARD_CATEGORICAL_DIM),
    ("card_numeric", CARD_CAPACITY * CARD_NUMERIC_DIM),
    ("card_numeric_known", CARD_CAPACITY * CARD_NUMERIC_DIM),
    ("card_valid", CARD_CAPACITY),
    ("enemy_features", MAX_ENEMIES * ENEMY_ENCODED_DIM),
    ("enemy_mask", MAX_ENEMIES),
    ("global", GLOBAL_ENCODED_DIM),
)
_flat_offset = 0
_flat_layout: list[tuple[str, int, int]] = []
for _flat_name, _flat_size in _FLAT_SIZES:
    _flat_layout.append((_flat_name, _flat_offset, _flat_offset + _flat_size))
    _flat_offset += _flat_size
FLAT_LAYOUT = tuple(_flat_layout)
FLAT_DIM = _flat_offset
del _flat_layout, _flat_offset, _flat_name, _flat_size


FlatInput = TypedDict(
    "FlatInput",
    {
        "card_categorical": NDArray[np.int64],
        "card_numeric": NDArray[np.float32],
        "card_numeric_known": NDArray[np.bool_],
        "card_valid": NDArray[np.bool_],
        "enemy_features": NDArray[np.float32],
        "enemy_mask": NDArray[np.bool_],
        "global": NDArray[np.float32],
        "action_mask": NDArray[np.bool_],
    },
)

TokenInput = TypedDict(
    "TokenInput",
    {
        "card_categorical": NDArray[np.int64],
        "card_numeric": NDArray[np.float32],
        "card_numeric_known": NDArray[np.bool_],
        "card_valid": NDArray[np.bool_],
        "enemy_features": NDArray[np.float32],
        "enemy_mask": NDArray[np.bool_],
        "global": NDArray[np.float32],
        "action_mask": NDArray[np.bool_],
    },
)


@dataclass(frozen=True)
class _PreparedInput:
    card_categorical: NDArray[np.int64]
    card_numeric: NDArray[np.float32]
    card_numeric_known: NDArray[np.bool_]
    card_valid: NDArray[np.bool_]
    enemy_features: NDArray[np.float32]
    enemy_mask: NDArray[np.bool_]
    global_values: NDArray[np.float32]
    action_mask: NDArray[np.bool_]


def _require_array(
    observation: Mapping[str, Any],
    key: str,
    shape: tuple[int, ...],
    dtype: np.dtype[Any],
) -> NDArray[Any]:
    if key not in observation:
        raise KeyError(f"规范观测缺少字段 {key!r}")
    result = np.asarray(observation[key])
    if result.shape != shape:
        raise ValueError(f"{key} shape 应为 {shape}，实际为 {result.shape}")
    if result.dtype != dtype:
        raise TypeError(f"{key} dtype 应为 {dtype}，实际为 {result.dtype}")
    return result.copy()


def _require_cards(observation: Mapping[str, Any], key: str) -> list[Any]:
    if key not in observation:
        raise KeyError(f"规范观测缺少字段 {key!r}")
    value = observation[key]
    if not isinstance(value, list):
        raise TypeError(f"{key} 应为 list，实际为 {type(value).__name__}")
    return value


def _integer(value: Any, field: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{field} 必须为整数")
    return int(value)


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{field} 必须为 bool")
    return bool(value)


def _validate_card(
    value: Any,
    *,
    expected_location: CardLocation,
    registry: CardRegistry,
    field: str,
) -> CardObservation:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} 必须为卡牌记录")
    required = {
        "card_id", "location", "upgraded", "cost", "cost_known", "target_kind"
    }
    missing = required.difference(value)
    if missing:
        raise KeyError(f"{field} 缺少字段 {sorted(missing)}")

    card_id = _integer(value["card_id"], f"{field}.card_id")
    location = _integer(value["location"], f"{field}.location")
    upgraded = _boolean(value["upgraded"], f"{field}.upgraded")
    cost = _integer(value["cost"], f"{field}.cost")
    cost_known = _boolean(value["cost_known"], f"{field}.cost_known")
    target_kind = _integer(value["target_kind"], f"{field}.target_kind")

    if card_id == PAD_ID:
        raise ValueError(f"{field}.card_id=PAD 不能表示真实卡牌")
    definition = registry.from_registry_id(card_id)
    if location != int(expected_location):
        raise ValueError(
            f"{field}.location 应为 {int(expected_location)}，实际为 {location}"
        )
    if target_kind != int(definition.target_kind):
        raise ValueError(
            f"{field}.target_kind 与注册表不一致：期望 {int(definition.target_kind)}，"
            f"实际为 {target_kind}"
        )
    if expected_location == CardLocation.HAND and not cost_known:
        raise ValueError(f"{field} 手牌费用必须已知")
    if expected_location != CardLocation.HAND and cost_known:
        raise ValueError(f"{field} 非手牌费用当前必须标记为未知")
    if not cost_known and cost != 0:
        raise ValueError(f"{field} 未知费用的占位值必须为 0")
    return {
        "card_id": card_id,
        "location": location,
        "upgraded": upgraded,
        "cost": cost,
        "cost_known": cost_known,
        "target_kind": target_kind,
    }


def _category_index(mapping: Mapping[int, int], value: int, field: str) -> int:
    try:
        return mapping[value]
    except KeyError as exc:
        raise ValueError(f"{field} 出现当前机制范围外的类别值 {value}") from exc


def _encode_enemies(
    source: NDArray[np.int32],
    enemy_mask: NDArray[np.bool_],
) -> NDArray[np.float32]:
    source[~enemy_mask] = 0
    encoded = np.zeros((MAX_ENEMIES, ENEMY_ENCODED_DIM), dtype=np.float32)
    numeric_start = len(MONSTER_CATEGORIES)
    intent_start = numeric_start + 6
    tail_start = intent_start + len(INTENT_CATEGORIES)
    for row_index in np.flatnonzero(enemy_mask):
        row = source[row_index]
        monster = _category_index(MONSTER_TO_INDEX, int(row[0]), "monster_id")
        intent = _category_index(INTENT_TO_INDEX, int(row[7]), "intent")
        encoded[row_index, monster] = 1.0
        encoded[row_index, numeric_start:intent_start] = row[1:7]
        encoded[row_index, intent_start + intent] = 1.0
        encoded[row_index, tail_start:] = row[8:12]
    return encoded


def _prepare(
    observation: Mapping[str, Any],
    registry: CardRegistry,
) -> _PreparedInput:
    """双 wrapper 的唯一预处理路径；验证后再写入固定容量张量。"""

    hand_values = _require_cards(observation, "hand")
    if len(hand_values) > MAX_HAND:
        raise ValueError(f"hand 超过容量 {MAX_HAND}：实际 {len(hand_values)}")
    hand = [
        _validate_card(
            card,
            expected_location=CardLocation.HAND,
            registry=registry,
            field=f"hand[{index}]",
        )
        for index, card in enumerate(hand_values)
    ]

    pile_groups: list[list[CardObservation]] = []
    for key, location in (
        ("draw_pile", CardLocation.DRAW),
        ("discard_pile", CardLocation.DISCARD),
        ("exhaust_pile", CardLocation.EXHAUST),
    ):
        records = [
            _validate_card(
                card,
                expected_location=location,
                registry=registry,
                field=f"{key}[{index}]",
            )
            for index, card in enumerate(_require_cards(observation, key))
        ]
        pile_groups.append(sorted(records, key=lambda card: (
            card["card_id"], card["upgraded"], card["cost_known"],
            card["cost"], card["target_kind"],
        )))
    piles = [card for group in pile_groups for card in group]
    if len(piles) > PILE_CAPACITY:
        raise ValueError(
            f"三个非手牌区域合计超过 pile_capacity={PILE_CAPACITY}：实际 {len(piles)}"
        )

    global_values = _require_array(
        observation, "global", (len(GLOBAL_FEATURES),), np.dtype(np.int32)
    )
    expected_counts = (len(hand), *(len(group) for group in pile_groups))
    actual_counts = tuple(map(int, global_values[5:9]))
    if actual_counts != expected_counts:
        raise ValueError(
            f"四区卡牌数量与 global 不一致：记录={expected_counts}，global={actual_counts}"
        )

    card_categorical = np.zeros(
        (CARD_CAPACITY, CARD_CATEGORICAL_DIM), dtype=np.int64
    )
    card_numeric = np.zeros((CARD_CAPACITY, CARD_NUMERIC_DIM), dtype=np.float32)
    card_numeric_known = np.zeros(
        (CARD_CAPACITY, CARD_NUMERIC_DIM), dtype=np.bool_
    )
    card_valid = np.zeros(CARD_CAPACITY, dtype=np.bool_)
    indexed_cards = [
        *((index, card) for index, card in enumerate(hand)),
        *((MAX_HAND + index, card) for index, card in enumerate(piles)),
    ]
    for row_index, card in indexed_cards:
        card_categorical[row_index] = (
            card["card_id"], card["location"], card["target_kind"], int(card["upgraded"])
        )
        card_numeric[row_index, 0] = float(card["cost"])
        card_numeric_known[row_index, 0] = card["cost_known"]
        card_valid[row_index] = True

    enemies = _require_array(
        observation,
        "enemies",
        (MAX_ENEMIES, len(ENEMY_FEATURES)),
        np.dtype(np.int32),
    )
    enemy_mask = _require_array(
        observation, "enemy_mask", (MAX_ENEMIES,), np.dtype(np.bool_)
    )
    action_mask = _require_array(
        observation, "action_mask", (ACTION_COUNT,), np.dtype(np.bool_)
    )
    return _PreparedInput(
        card_categorical=card_categorical,
        card_numeric=card_numeric,
        card_numeric_known=card_numeric_known,
        card_valid=card_valid,
        enemy_features=_encode_enemies(enemies, enemy_mask),
        enemy_mask=enemy_mask,
        global_values=global_values.astype(np.float32),
        action_mask=action_mask,
    )


class _ObservationWrapper:
    """保留环境控制流，只替换观测表示。"""

    def __init__(self, env: LightspeedBattleEnv) -> None:
        self.env = env

    @property
    def max_turns(self) -> int:
        return self.env.max_turns

    @property
    def gamma(self) -> float:
        return self.env.gamma

    @property
    def schema_version(self) -> int:
        return self.env.schema_version

    @property
    def registry_version(self) -> int:
        return self.env.registry_version

    @property
    def registry_hash(self) -> str:
        return self.env.registry_hash

    def reset(self, *args: Any, **kwargs: Any) -> Any:
        return self.transform(self.env.reset(*args, **kwargs))

    def step(self, action: int) -> tuple[Any, float, bool, bool, dict[str, int]]:
        observation, reward, terminated, truncated, info = self.env.step(action)
        return self.transform(observation), reward, terminated, truncated, info

    def observation(self) -> Any:
        return self.transform(self.env.observation())

    def action_mask(self) -> NDArray[np.bool_]:
        return self.env.action_mask()

    def transform(self, observation: Mapping[str, Any]) -> Any:
        raise NotImplementedError


class FlattenWrapper(_ObservationWrapper):
    """分别展平实体轴，供 MLP 在模型内编码类别后拼接。"""

    def transform(self, observation: Mapping[str, Any]) -> FlatInput:
        prepared = _prepare(observation, self.env.registry)
        return {
            "card_categorical": prepared.card_categorical.ravel().copy(),
            "card_numeric": prepared.card_numeric.ravel().copy(),
            "card_numeric_known": prepared.card_numeric_known.ravel().copy(),
            "card_valid": prepared.card_valid.copy(),
            "enemy_features": prepared.enemy_features.ravel().copy(),
            "enemy_mask": prepared.enemy_mask.copy(),
            "global": prepared.global_values.copy(),
            "action_mask": prepared.action_mask.copy(),
        }


class TokenWrapper(_ObservationWrapper):
    """保留实体轴，供模型内类型专用投影和 Set Transformer 使用。"""

    def transform(self, observation: Mapping[str, Any]) -> TokenInput:
        prepared = _prepare(observation, self.env.registry)
        return {
            "card_categorical": prepared.card_categorical.copy(),
            "card_numeric": prepared.card_numeric.copy(),
            "card_numeric_known": prepared.card_numeric_known.copy(),
            "card_valid": prepared.card_valid.copy(),
            "enemy_features": prepared.enemy_features.copy(),
            "enemy_mask": prepared.enemy_mask.copy(),
            "global": prepared.global_values.reshape(1, GLOBAL_ENCODED_DIM).copy(),
            "action_mask": prepared.action_mask.copy(),
        }
