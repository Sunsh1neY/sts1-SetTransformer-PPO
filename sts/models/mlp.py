"""D25 最小切片使用的 MLP policy/value 与输入、checkpoint 契约。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence, TypedDict

import numpy as np
import torch
from torch import Tensor, nn
from torch.distributions import Categorical

from sts.env.lightspeed import ACTION_COUNT, MAX_ENEMIES
from sts.env.registry import (
    DEFAULT_CARD_REGISTRY,
    SCHEMA_VERSION,
    CardRegistry,
)
from sts.env.wrappers import (
    CARD_CAPACITY,
    CARD_CATEGORICAL_DIM,
    CARD_NUMERIC_DIM,
    ENEMY_ENCODED_DIM,
    GLOBAL_ENCODED_DIM,
    FlatInput,
)


# 固定尺度只改数量级，不裁剪信息；后续 Set 编码器须复用。
NUMERIC_ENCODING_VERSION = 1
CARD_NUMERIC_SCALES = (3.0,)
ENEMY_NUMERIC_SCALES = (
    1., 1., 1., 1.,  # 四种敌人 one-hot。
    100., 100., 100., 10., 10., 10.,  # HP/max_hp/block/strength/vulnerable/weak。
    1., 1., 1., 1., 1., 1.,  # 六种可见意图 one-hot。
    100., 10., 10., 10.,  # intent_damage/hits/curl_up/ritual。
)
GLOBAL_NUMERIC_SCALES = (
    100., 100., 100., 3., 50., 10., 10., 10., 10., 100., 10., 10., 10.,
)


class FlatBatch(TypedDict):
    """FlattenWrapper 观测组成的批量 torch 张量。"""

    card_categorical: Tensor
    card_numeric: Tensor
    card_numeric_known: Tensor
    card_valid: Tensor
    enemy_features: Tensor
    enemy_mask: Tensor
    global_values: Tensor
    action_mask: Tensor


@dataclass(frozen=True)
class MlpConfig:
    """保持结构显式的小型 MLP 配置。"""

    card_vocab_size: int
    card_embedding_dim: int = 8
    location_embedding_dim: int = 3
    target_embedding_dim: int = 2
    upgraded_embedding_dim: int = 2
    card_numeric_projection_dim: int = 4
    enemy_projection_dim: int = 16
    global_projection_dim: int = 16
    hidden_dim: int = 128

    @classmethod
    def from_registry(cls, registry: CardRegistry = DEFAULT_CARD_REGISTRY) -> MlpConfig:
        """按最大稳定 ID 确定词表宽度；0 保留给 PAD。"""

        return cls(
            card_vocab_size=max(entry.registry_id for entry in registry.entries) + 1
        )

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if value <= 0:
                raise ValueError(f"{name} 必须为正整数")


def _stack_field(
    observations: Sequence[Mapping[str, Any]],
    key: str,
    *,
    shape: tuple[int, ...],
    dtype: np.dtype[Any],
) -> np.ndarray[Any, Any]:
    values: list[np.ndarray[Any, Any]] = []
    for index, observation in enumerate(observations):
        if key not in observation:
            raise KeyError(f"第 {index} 个 FlatInput 缺少字段 {key!r}")
        value = np.asarray(observation[key])
        if value.shape != shape:
            raise ValueError(
                f"第 {index} 个 {key} shape 应为 {shape}，实际为 {value.shape}"
            )
        if value.dtype != dtype:
            raise TypeError(
                f"第 {index} 个 {key} dtype 应为 {dtype}，实际为 {value.dtype}"
            )
        values.append(value)
    return np.stack(values, axis=0)


def batch_flat_inputs(
    observations: Sequence[FlatInput],
    *,
    device: torch.device | str | None = None,
) -> FlatBatch:
    """严格检查并批量化 FlatInput，不在此处引入可训练变换。"""

    if not observations:
        raise ValueError("至少需要一个 FlatInput 才能组成批量")
    categorical = _stack_field(
        observations,
        "card_categorical",
        shape=(CARD_CAPACITY * CARD_CATEGORICAL_DIM,),
        dtype=np.dtype(np.int64),
    )
    numeric = _stack_field(
        observations,
        "card_numeric",
        shape=(CARD_CAPACITY * CARD_NUMERIC_DIM,),
        dtype=np.dtype(np.float32),
    )
    numeric_known = _stack_field(
        observations,
        "card_numeric_known",
        shape=(CARD_CAPACITY * CARD_NUMERIC_DIM,),
        dtype=np.dtype(np.bool_),
    )
    card_valid = _stack_field(
        observations,
        "card_valid",
        shape=(CARD_CAPACITY,),
        dtype=np.dtype(np.bool_),
    )
    enemies = _stack_field(
        observations,
        "enemy_features",
        shape=(MAX_ENEMIES * ENEMY_ENCODED_DIM,),
        dtype=np.dtype(np.float32),
    )
    enemy_mask = _stack_field(
        observations,
        "enemy_mask",
        shape=(MAX_ENEMIES,),
        dtype=np.dtype(np.bool_),
    )
    global_values = _stack_field(
        observations,
        "global",
        shape=(GLOBAL_ENCODED_DIM,),
        dtype=np.dtype(np.float32),
    )
    action_mask = _stack_field(
        observations,
        "action_mask",
        shape=(ACTION_COUNT,),
        dtype=np.dtype(np.bool_),
    )
    return {
        "card_categorical": torch.as_tensor(categorical, device=device),
        "card_numeric": torch.as_tensor(numeric, device=device),
        "card_numeric_known": torch.as_tensor(numeric_known, device=device),
        "card_valid": torch.as_tensor(card_valid, device=device),
        "enemy_features": torch.as_tensor(enemies, device=device),
        "enemy_mask": torch.as_tensor(enemy_mask, device=device),
        "global_values": torch.as_tensor(global_values, device=device),
        "action_mask": torch.as_tensor(action_mask, device=device),
    }


class MlpActorCritic(nn.Module):
    """类别先查表、数值按类型投影，再 flatten 的 actor-critic。"""

    def __init__(self, config: MlpConfig) -> None:
        super().__init__()
        self.config = config
        self.register_buffer("card_scales", torch.tensor(CARD_NUMERIC_SCALES))
        self.register_buffer("enemy_scales", torch.tensor(ENEMY_NUMERIC_SCALES))
        self.register_buffer("global_scales", torch.tensor(GLOBAL_NUMERIC_SCALES))
        self.card_embedding = nn.Embedding(
            config.card_vocab_size,
            config.card_embedding_dim,
            padding_idx=0,
        )
        self.location_embedding = nn.Embedding(
            5,
            config.location_embedding_dim,
            padding_idx=0,
        )
        self.target_embedding = nn.Embedding(
            3,
            config.target_embedding_dim,
            padding_idx=0,
        )
        # upgraded=0 同时可能是真实未升级卡，不能把 0 当 padding；最终由 card_valid 清零。
        self.upgraded_embedding = nn.Embedding(2, config.upgraded_embedding_dim)
        self.card_numeric_projection = nn.Sequential(
            nn.Linear(CARD_NUMERIC_DIM * 2, config.card_numeric_projection_dim),
            nn.Tanh(),
        )
        self.enemy_projection = nn.Sequential(
            nn.Linear(ENEMY_ENCODED_DIM, config.enemy_projection_dim),
            nn.Tanh(),
        )
        self.global_projection = nn.Sequential(
            nn.Linear(GLOBAL_ENCODED_DIM, config.global_projection_dim),
            nn.Tanh(),
        )

        card_dim = (
            config.card_embedding_dim
            + config.location_embedding_dim
            + config.target_embedding_dim
            + config.upgraded_embedding_dim
            + config.card_numeric_projection_dim
            + 1
        )
        trunk_input_dim = (
            CARD_CAPACITY * card_dim
            + MAX_ENEMIES * config.enemy_projection_dim
            + MAX_ENEMIES
            + config.global_projection_dim
        )
        self.trunk = nn.Sequential(
            nn.Linear(trunk_input_dim, config.hidden_dim),
            nn.Tanh(),
            nn.Linear(config.hidden_dim, config.hidden_dim),
            nn.Tanh(),
        )
        self.policy_head = nn.Linear(config.hidden_dim, ACTION_COUNT)
        self.value_head = nn.Linear(config.hidden_dim, 1)

    def _encode(self, batch: FlatBatch) -> Tensor:
        categorical = batch["card_categorical"].reshape(
            -1, CARD_CAPACITY, CARD_CATEGORICAL_DIM
        )
        if categorical.min().item() < 0:
            raise ValueError("card_categorical 不能包含负类别")
        if categorical[:, :, 0].max().item() >= self.config.card_vocab_size:
            raise ValueError("card_id 超过当前 MLP checkpoint 的词表范围")

        card_numeric = batch["card_numeric"].reshape(
            -1, CARD_CAPACITY, CARD_NUMERIC_DIM
        )
        numeric_known = batch["card_numeric_known"].reshape(
            -1, CARD_CAPACITY, CARD_NUMERIC_DIM
        )
        card_valid = batch["card_valid"].reshape(-1, CARD_CAPACITY, 1)
        card_parts = (
            self.card_embedding(categorical[:, :, 0]),
            self.location_embedding(categorical[:, :, 1]),
            self.target_embedding(categorical[:, :, 2]),
            self.upgraded_embedding(categorical[:, :, 3]),
            self.card_numeric_projection(
                torch.cat((card_numeric / self.card_scales, numeric_known.float()), dim=-1)
            ),
            card_valid.float(),
        )
        cards = torch.cat(card_parts, dim=-1) * card_valid.float()

        enemies = batch["enemy_features"].reshape(
            -1, MAX_ENEMIES, ENEMY_ENCODED_DIM
        )
        enemy_mask = batch["enemy_mask"].reshape(-1, MAX_ENEMIES, 1)
        encoded_enemies = self.enemy_projection(enemies / self.enemy_scales) * enemy_mask.float()
        global_values = self.global_projection(batch["global_values"] / self.global_scales)
        flat = torch.cat(
            (
                cards.flatten(start_dim=1),
                encoded_enemies.flatten(start_dim=1),
                enemy_mask.float().flatten(start_dim=1),
                global_values,
            ),
            dim=1,
        )
        return self.trunk(flat)

    def forward(self, batch: FlatBatch) -> tuple[Tensor, Tensor]:
        """返回未屏蔽 logits 与 value；掩码必须在构造分布前施加。"""

        hidden = self._encode(batch)
        return self.policy_head(hidden), self.value_head(hidden).squeeze(-1)

    def distribution_and_value(
        self,
        batch: FlatBatch,
    ) -> tuple[Categorical, Tensor, Tensor]:
        """用环境 mask 构造策略分布，并同时返回 value 与 masked logits。"""

        logits, value = self(batch)
        action_mask = batch["action_mask"]
        if action_mask.shape != logits.shape:
            raise ValueError(
                f"action_mask shape 应为 {tuple(logits.shape)}，"
                f"实际为 {tuple(action_mask.shape)}"
            )
        if action_mask.dtype != torch.bool:
            raise TypeError("action_mask 必须为 torch.bool")
        if not action_mask.any(dim=1).all():
            raise ValueError("每个非终局样本至少需要一个合法动作")
        masked_logits = logits.masked_fill(~action_mask, -torch.inf)
        return Categorical(logits=masked_logits), value, masked_logits

    def action_and_value(
        self,
        batch: FlatBatch,
        action: Tensor | None = None,
    ) -> tuple[Tensor, Tensor, Tensor, Tensor, Tensor]:
        """采样或复算给定动作，供 PPO 用同一掩码后分布计算损失。"""

        distribution, value, masked_logits = self.distribution_and_value(batch)
        if action is not None:
            if not isinstance(action, Tensor) or action.dtype != torch.long:
                raise TypeError("action 必须为 torch.int64 张量")
            if action.shape != value.shape:
                raise ValueError(
                    f"action shape 应为 {tuple(value.shape)}，实际为 {tuple(action.shape)}"
                )
            if action.device != masked_logits.device:
                raise ValueError("action 与模型输出必须位于同一设备")
            if ((action < 0) | (action >= ACTION_COUNT)).any():
                raise ValueError(f"action 必须在 0..{ACTION_COUNT - 1}")
            if not batch["action_mask"].gather(1, action[:, None]).all():
                raise ValueError("action 包含当前观测中的非法动作")
        chosen = distribution.sample() if action is None else action
        return (
            chosen,
            distribution.log_prob(chosen),
            distribution.entropy(),
            value,
            masked_logits,
        )


def _checkpoint_contract(registry: CardRegistry) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "registry_version": registry.version,
        "registry_hash": registry.content_hash,
        "numeric_encoding_version": NUMERIC_ENCODING_VERSION,
        "card_scales": CARD_NUMERIC_SCALES,
        "enemy_scales": ENEMY_NUMERIC_SCALES,
        "global_scales": GLOBAL_NUMERIC_SCALES,
    }


def _check_registry_capacity(config: MlpConfig, registry: CardRegistry) -> None:
    """版本标签匹配之外，词表还必须实际容纳注册表里的每个 ID。"""

    required_size = MlpConfig.from_registry(registry).card_vocab_size
    if config.card_vocab_size < required_size:
        raise ValueError(
            f"MLP 词表容量不足：需要至少 {required_size}，实际为 {config.card_vocab_size}"
        )


def save_mlp_checkpoint(
    path: str | Path,
    model: MlpActorCritic,
    *,
    registry: CardRegistry = DEFAULT_CARD_REGISTRY,
    optimizer: torch.optim.Optimizer | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    """保存带输入契约的 checkpoint，避免扩容后静默载入旧词表。"""

    _check_registry_capacity(model.config, registry)
    payload: dict[str, Any] = {
        "format_version": 2,
        "input_contract": _checkpoint_contract(registry),
        "model_config": asdict(model.config),
        "model_state_dict": model.state_dict(),
        "extra": dict(extra or {}),
    }
    if optimizer is not None:
        payload["optimizer_state_dict"] = optimizer.state_dict()
    torch.save(payload, Path(path))


def load_mlp_checkpoint(
    path: str | Path,
    *,
    registry: CardRegistry = DEFAULT_CARD_REGISTRY,
    device: torch.device | str = "cpu",
) -> tuple[MlpActorCritic, dict[str, Any]]:
    """只加载与当前 schema 和注册表完全匹配的 MLP checkpoint。"""

    payload = torch.load(Path(path), map_location=device, weights_only=True)
    if not isinstance(payload, dict):
        raise TypeError("MLP checkpoint 顶层必须为 dict")
    if payload.get("format_version") != 2:
        raise ValueError("不支持的 MLP checkpoint format_version")
    expected = _checkpoint_contract(registry)
    if payload.get("input_contract") != expected:
        raise ValueError(
            f"MLP checkpoint 输入契约不匹配：期望 {expected}，"
            f"实际 {payload.get('input_contract')}"
        )
    config = MlpConfig(**payload["model_config"])
    _check_registry_capacity(config, registry)
    model = MlpActorCritic(config).to(device)
    for name in ("card_scales", "enemy_scales", "global_scales"):
        if not torch.equal(payload["model_state_dict"][name], model.state_dict()[name]):
            raise ValueError(f"checkpoint 缩放常量 {name} 与当前模型不一致")
    model.load_state_dict(payload["model_state_dict"])
    return model, payload
