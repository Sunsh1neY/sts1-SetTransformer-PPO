"""使用独立 NumPy 随机流采样的 MLP 推理 Agent。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import torch

from sts.agents.masked_policy import AgentDecision
from sts.env.lightspeed import ACTION_COUNT
from sts.models.mlp import MlpActorCritic, batch_flat_inputs


class MlpAgent:
    """只读取 FlatInput；诊断采样不消耗训练所用的 torch 随机流。"""

    def __init__(self, model: MlpActorCritic, seed: int | None = None) -> None:
        self.model = model
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def decide(self, observation: Mapping[str, Any]) -> AgentDecision:
        """在 eval/no_grad 下取得掩码后概率，返回原动作编号。"""

        device = next(self.model.parameters()).device
        batch = batch_flat_inputs([observation], device=device)
        # 保留各子模块模式，兼容调用方将某个子模块单独设为 eval 的情况。
        modes = [(module, module.training) for module in self.model.modules()]
        try:
            self.model.eval()
            with torch.no_grad():
                distribution, _, _ = self.model.distribution_and_value(batch)
                probabilities = distribution.probs[0].cpu().numpy().astype(np.float64)
        finally:
            for module, training in modes:
                module.training = training

        mask = np.asarray(observation["action_mask"])
        if not np.isfinite(probabilities).all() or (probabilities < 0).any():
            raise ValueError("MLP 概率必须是有限非负数")
        if (probabilities[~mask] != 0).any():
            raise ValueError("MLP 掩码后分布包含非法动作概率")
        total = probabilities[mask].sum()
        if not np.isfinite(total) or total <= 0:
            raise ValueError("MLP 合法动作概率总和必须为有限正数")
        # float32 softmax 转 float64 后重新归一化，以满足 NumPy choice 的精度要求。
        probabilities[mask] /= total
        action = int(self._rng.choice(ACTION_COUNT, p=probabilities))
        return AgentDecision(probabilities=probabilities, action=action)
