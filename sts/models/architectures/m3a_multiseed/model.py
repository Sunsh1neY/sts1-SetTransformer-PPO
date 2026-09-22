"""Four shared-parameter PMA seeds, fixed-order concatenation, unchanged M2a actor."""
import torch
from torch import nn
from ..critic_common import CriticVariant

class M3aActorCritic(CriticVariant):
    model_version = "a-path-m3a-critic-four-seed-v1"
    def __init__(self):
        super().__init__()
        first = self.critic_pool_seed.detach().clone()
        self.critic_pool_seed = nn.Parameter(torch.cat([first, torch.randn(1, 3, 64)*.02], dim=1))
        self.value_head[0] = nn.Linear(256, 64)

    def _pool_branch(self, h, valid, critic=False):
        if not critic:
            return super()._pool_branch(h, valid, critic=False)
        q = self.critic_pool_seed.expand(len(h), -1, -1)
        pooled = q + self.critic_pool(q, h, h, key_padding_mask=~valid, need_weights=False)[0]
        pooled = pooled + self.critic_pool_ff(self.critic_pool_norm(pooled))
        return self.critic_pool_final(pooled).flatten(1)
