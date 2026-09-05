"""正式 Agent 的动作分布、单次决策及 NumPy masked softmax。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray

from sts.env.lightspeed import ACTION_COUNT


def _checked_action_mask(values: Any) -> NDArray[np.bool_]:
    mask = np.asarray(values)
    if mask.shape != (ACTION_COUNT,):
        raise ValueError(f"action_mask shape 应为 ({ACTION_COUNT},)，实际为 {mask.shape}")
    if mask.dtype != np.bool_:
        raise TypeError(f"action_mask dtype 应为 bool，实际为 {mask.dtype}")
    return mask


def masked_softmax(
    logits: Any,
    action_mask: Any,
) -> NDArray[np.float64]:
    """先屏蔽非法动作，再仅在合法动作集合上计算稳定 softmax。"""

    scores = np.asarray(logits, dtype=np.float64)
    mask = np.asarray(action_mask)
    if scores.ndim != 1:
        raise ValueError(f"logits 必须是一维，实际 shape 为 {scores.shape}")
    if mask.shape != scores.shape:
        raise ValueError(
            f"action_mask shape 必须与 logits 相同，实际为 {mask.shape} 和 {scores.shape}"
        )
    if mask.dtype != np.bool_:
        raise TypeError(f"action_mask dtype 应为 bool，实际为 {mask.dtype}")
    if not mask.any():
        raise ValueError("没有合法动作，不能构造概率分布")
    if not np.isfinite(scores[mask]).all():
        raise ValueError("合法动作的 logits 必须都是有限数")

    probabilities = np.zeros(scores.shape, dtype=np.float64)
    legal_scores = scores[mask]
    # 减去最大值不会改变比例，并避免 exp 在大正数上溢出。
    weights = np.exp(legal_scores - legal_scores.max())
    probabilities[mask] = weights / weights.sum()
    return probabilities


@dataclass(frozen=True)
class AgentDecision:
    """统一 Agent 输出：完整策略分布，以及从中抽到的原动作编号。"""

    probabilities: NDArray[np.float64]
    action: int


class MaskedRandomAgent:
    """用统一 31 维接口实现的正式随机 Agent。"""

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def decide(self, observation: Mapping[str, Any]) -> AgentDecision:
        """在 Agent 内形成合法分布、完成抽样并返回固定宽度决策。"""

        if "action_mask" not in observation:
            raise KeyError("观测缺少 action_mask")
        mask = _checked_action_mask(observation["action_mask"])
        logits = np.zeros(ACTION_COUNT, dtype=np.float64)
        probabilities = masked_softmax(logits, mask)
        action = int(self._rng.choice(ACTION_COUNT, p=probabilities))
        return AgentDecision(
            probabilities=probabilities,
            action=action,
        )
