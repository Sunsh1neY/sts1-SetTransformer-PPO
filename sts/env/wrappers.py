"""从同一规范观测派生 MLP 与 Set Transformer 的确定性输入。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, TypedDict

import numpy as np
from numpy.typing import NDArray

from sts.env.lightspeed import (
    ACTION_COUNT,
    ENEMY_FEATURES,
    GLOBAL_FEATURES,
    HAND_FEATURES,
    MAX_ENEMIES,
    MAX_HAND,
    PILE_FEATURES,
    LightspeedBattleEnv,
    Observation,
)


# 类别整数只用于查表。顺序是本项目特征契约，不表达大小关系。
CARD_CATEGORIES = (25, 104, 321)  # Bash、Defend、Strike
MONSTER_CATEGORIES = (14, 23, 28, 37)  # Cultist、Green Louse、Jaw Worm、Red Louse
INTENT_CATEGORIES = (0, 1, 2, 3, 4, 5)

CARD_TO_INDEX = {value: index for index, value in enumerate(CARD_CATEGORIES)}
MONSTER_TO_INDEX = {value: index for index, value in enumerate(MONSTER_CATEGORIES)}
INTENT_TO_INDEX = {value: index for index, value in enumerate(INTENT_CATEGORIES)}

HAND_ENCODED_FEATURES = (
    "card_is_bash",
    "card_is_defend",
    "card_is_strike",
    "upgraded",
    "cost",
)
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

HAND_ENCODED_DIM = len(HAND_ENCODED_FEATURES)
ENEMY_ENCODED_DIM = len(ENEMY_ENCODED_FEATURES)
GLOBAL_ENCODED_DIM = len(GLOBAL_FEATURES)
PILE_ENCODED_DIM = len(PILE_FEATURES)
TOKEN_COUNT = 3 + MAX_HAND + MAX_ENEMIES

_HAND_FLAT_SIZE = MAX_HAND * HAND_ENCODED_DIM
_ENEMY_FLAT_SIZE = MAX_ENEMIES * ENEMY_ENCODED_DIM
_GLOBAL_FLAT_SIZE = GLOBAL_ENCODED_DIM
_PILE_FLAT_SIZE = PILE_ENCODED_DIM
_HAND_MASK_FLAT_SIZE = MAX_HAND
_ENEMY_MASK_FLAT_SIZE = MAX_ENEMIES

FLAT_LAYOUT = (
    ("hand", 0, _HAND_FLAT_SIZE),
    ("enemies", _HAND_FLAT_SIZE, _HAND_FLAT_SIZE + _ENEMY_FLAT_SIZE),
    (
        "global",
        _HAND_FLAT_SIZE + _ENEMY_FLAT_SIZE,
        _HAND_FLAT_SIZE + _ENEMY_FLAT_SIZE + _GLOBAL_FLAT_SIZE,
    ),
    (
        "draw_pile",
        _HAND_FLAT_SIZE + _ENEMY_FLAT_SIZE + _GLOBAL_FLAT_SIZE,
        _HAND_FLAT_SIZE
        + _ENEMY_FLAT_SIZE
        + _GLOBAL_FLAT_SIZE
        + _PILE_FLAT_SIZE,
    ),
    (
        "discard_pile",
        _HAND_FLAT_SIZE
        + _ENEMY_FLAT_SIZE
        + _GLOBAL_FLAT_SIZE
        + _PILE_FLAT_SIZE,
        _HAND_FLAT_SIZE
        + _ENEMY_FLAT_SIZE
        + _GLOBAL_FLAT_SIZE
        + 2 * _PILE_FLAT_SIZE,
    ),
    (
        "hand_mask",
        _HAND_FLAT_SIZE
        + _ENEMY_FLAT_SIZE
        + _GLOBAL_FLAT_SIZE
        + 2 * _PILE_FLAT_SIZE,
        _HAND_FLAT_SIZE
        + _ENEMY_FLAT_SIZE
        + _GLOBAL_FLAT_SIZE
        + 2 * _PILE_FLAT_SIZE
        + _HAND_MASK_FLAT_SIZE,
    ),
    (
        "enemy_mask",
        _HAND_FLAT_SIZE
        + _ENEMY_FLAT_SIZE
        + _GLOBAL_FLAT_SIZE
        + 2 * _PILE_FLAT_SIZE
        + _HAND_MASK_FLAT_SIZE,
        _HAND_FLAT_SIZE
        + _ENEMY_FLAT_SIZE
        + _GLOBAL_FLAT_SIZE
        + 2 * _PILE_FLAT_SIZE
        + _HAND_MASK_FLAT_SIZE
        + _ENEMY_MASK_FLAT_SIZE,
    ),
)
FLAT_DIM = FLAT_LAYOUT[-1][2]


class FlattenObservation(TypedDict):
    """MLP 输入及环境提供的合法动作 mask。"""

    features: NDArray[np.float32]
    action_mask: NDArray[np.bool_]


TokenObservation = TypedDict(
    "TokenObservation",
    {
        "hand": NDArray[np.float32],
        "enemies": NDArray[np.float32],
        "draw_pile": NDArray[np.float32],
        "discard_pile": NDArray[np.float32],
        "global": NDArray[np.float32],
        "hand_mask": NDArray[np.bool_],
        "enemy_mask": NDArray[np.bool_],
        "token_mask": NDArray[np.bool_],
        "action_mask": NDArray[np.bool_],
    },
)


@dataclass(frozen=True)
class _EncodedGroups:
    hand: NDArray[np.float32]
    enemies: NDArray[np.float32]
    draw_pile: NDArray[np.float32]
    discard_pile: NDArray[np.float32]
    global_values: NDArray[np.float32]
    hand_mask: NDArray[np.bool_]
    enemy_mask: NDArray[np.bool_]
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


def _canonical_arrays(observation: Mapping[str, Any]) -> Observation:
    """再次执行边界清理，使 wrapper 不信任无效行里的残留值。"""

    hand = _require_array(
        observation,
        "hand",
        (MAX_HAND, len(HAND_FEATURES)),
        np.dtype(np.int32),
    )
    enemies = _require_array(
        observation,
        "enemies",
        (MAX_ENEMIES, len(ENEMY_FEATURES)),
        np.dtype(np.int32),
    )
    global_values = _require_array(
        observation,
        "global",
        (len(GLOBAL_FEATURES),),
        np.dtype(np.int32),
    )
    draw_pile = _require_array(
        observation,
        "draw_pile",
        (len(PILE_FEATURES),),
        np.dtype(np.int32),
    )
    discard_pile = _require_array(
        observation,
        "discard_pile",
        (len(PILE_FEATURES),),
        np.dtype(np.int32),
    )
    hand_mask = _require_array(
        observation,
        "hand_mask",
        (MAX_HAND,),
        np.dtype(np.bool_),
    )
    enemy_mask = _require_array(
        observation,
        "enemy_mask",
        (MAX_ENEMIES,),
        np.dtype(np.bool_),
    )
    action_mask = _require_array(
        observation,
        "action_mask",
        (ACTION_COUNT,),
        np.dtype(np.bool_),
    )
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


def _category_index(mapping: Mapping[int, int], value: int, field: str) -> int:
    try:
        return mapping[value]
    except KeyError as exc:
        raise ValueError(f"{field} 出现当前机制范围外的类别值 {value}") from exc


def _encode_groups(observation: Mapping[str, Any]) -> _EncodedGroups:
    source = _canonical_arrays(observation)
    hand = np.zeros((MAX_HAND, HAND_ENCODED_DIM), dtype=np.float32)
    enemies = np.zeros((MAX_ENEMIES, ENEMY_ENCODED_DIM), dtype=np.float32)

    for row_index in np.flatnonzero(source["hand_mask"]):
        row = source["hand"][row_index]
        category = _category_index(CARD_TO_INDEX, int(row[0]), "card_id")
        hand[row_index, category] = 1.0
        hand[row_index, len(CARD_CATEGORIES)] = float(row[1])
        hand[row_index, len(CARD_CATEGORIES) + 1] = float(row[2])

    enemy_numeric_start = len(MONSTER_CATEGORIES)
    intent_start = enemy_numeric_start + 6
    enemy_tail_start = intent_start + len(INTENT_CATEGORIES)
    for row_index in np.flatnonzero(source["enemy_mask"]):
        row = source["enemies"][row_index]
        monster = _category_index(MONSTER_TO_INDEX, int(row[0]), "monster_id")
        intent = _category_index(INTENT_TO_INDEX, int(row[7]), "intent")
        enemies[row_index, monster] = 1.0
        enemies[row_index, enemy_numeric_start:intent_start] = row[1:7]
        enemies[row_index, intent_start + intent] = 1.0
        enemies[row_index, enemy_tail_start:] = row[8:12]

    return _EncodedGroups(
        hand=hand,
        enemies=enemies,
        draw_pile=source["draw_pile"].astype(np.float32),
        discard_pile=source["discard_pile"].astype(np.float32),
        global_values=source["global"].astype(np.float32),
        hand_mask=source["hand_mask"],
        enemy_mask=source["enemy_mask"],
        action_mask=source["action_mask"],
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

    def reset(self, *args: Any, **kwargs: Any) -> Any:
        return self.transform(self.env.reset(*args, **kwargs))

    def step(self, action: int) -> tuple[Any, float, bool, bool, dict[str, int]]:
        observation, reward, terminated, truncated, info = self.env.step(action)
        return (
            self.transform(observation),
            reward,
            terminated,
            truncated,
            info,
        )

    def observation(self) -> Any:
        return self.transform(self.env.observation())

    def action_mask(self) -> NDArray[np.bool_]:
        return self.env.action_mask()

    def transform(self, observation: Mapping[str, Any]) -> Any:
        raise NotImplementedError


class FlattenWrapper(_ObservationWrapper):
    """把共享实体编码按公开布局展开成 MLP 的一维输入。"""

    def transform(self, observation: Mapping[str, Any]) -> FlattenObservation:
        encoded = _encode_groups(observation)
        features = np.concatenate(
            (
                encoded.hand.ravel(),
                encoded.enemies.ravel(),
                encoded.global_values,
                encoded.draw_pile,
                encoded.discard_pile,
                encoded.hand_mask.astype(np.float32),
                encoded.enemy_mask.astype(np.float32),
            )
        ).astype(np.float32, copy=False)
        if features.shape != (FLAT_DIM,):
            raise RuntimeError(f"FlattenWrapper 内部布局错误：{features.shape}")
        return {
            "features": features,
            "action_mask": encoded.action_mask.copy(),
        }


class TokenWrapper(_ObservationWrapper):
    """保留实体行，供模型内类型专用投影和 Set Transformer 使用。"""

    def transform(self, observation: Mapping[str, Any]) -> TokenObservation:
        encoded = _encode_groups(observation)
        token_mask = np.concatenate(
            (
                np.ones(3, dtype=np.bool_),
                encoded.hand_mask,
                encoded.enemy_mask,
            )
        )
        return {
            "hand": encoded.hand.copy(),
            "enemies": encoded.enemies.copy(),
            "draw_pile": encoded.draw_pile.reshape(1, PILE_ENCODED_DIM).copy(),
            "discard_pile": encoded.discard_pile.reshape(1, PILE_ENCODED_DIM).copy(),
            "global": encoded.global_values.reshape(1, GLOBAL_ENCODED_DIM).copy(),
            "hand_mask": encoded.hand_mask.copy(),
            "enemy_mask": encoded.enemy_mask.copy(),
            "token_mask": token_mask,
            "action_mask": encoded.action_mask.copy(),
        }
