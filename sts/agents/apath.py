"""A路径Agent只读公开观测，返回一次环境推进所需的完整动作。"""
from dataclasses import dataclass

import torch

from sts.models.apath import ActionSample, batch_samples, encode


@dataclass
class APathDecision:
    samples: list[ActionSample]
    source: torch.Tensor
    target: torch.Tensor
    logp: torch.Tensor
    value: torch.Tensor
    routes: list[dict]


class APathAgent:
    """显式两阶段随机采样；没有环境句柄，不可推进或读取活动环境。"""

    def __init__(self, model, seed):
        self.model = model
        self.device = next(model.parameters()).device
        self.rng = torch.Generator(device=self.device).manual_seed(seed)

    @torch.no_grad()
    def act(self, observations):
        samples = [encode(obs) for obs in observations]
        source, target, logp, value = self.model.act(batch_samples(samples, self.device), self.rng)
        routes = [sample.route(u, j) for sample, u, j in
                  zip(samples, source.cpu().tolist(), target.cpu().tolist())]
        return APathDecision(samples, source, target, logp, value, routes)

    def evaluate_actions(self, samples, source, target):
        return self.model.evaluate_actions(batch_samples(samples, self.device),
                                           source.to(self.device), target.to(self.device))

    @torch.no_grad()
    def value_only(self, observations):
        return self.model.value_only(batch_samples([encode(obs) for obs in observations], self.device))

    def rng_state(self):
        return self.rng.get_state().clone()

    def restore_rng(self, state):
        self.rng.set_state(state.cpu())
