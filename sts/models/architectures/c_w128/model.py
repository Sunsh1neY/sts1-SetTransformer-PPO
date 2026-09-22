"""128-wide private critic, retaining shared width 64 and M2a actor."""
import torch
from torch import nn
from sts.models.entities import EntityArchitecture, EntityBlock
from ..critic_common import CriticVariant

class CW128ActorCritic(CriticVariant):
    model_version = "a-path-critic-width128-v1"
    def __init__(self):
        super().__init__()
        self.critic_input = nn.Linear(64, 128)
        architecture = EntityArchitecture(width=128, heads=4, ff_width=256)
        self.critic_blocks = nn.ModuleList([EntityBlock(architecture) for _ in range(2)])
        self.critic_final_norm = nn.LayerNorm(128)
        self.critic_pool_seed = nn.Parameter(torch.randn(1, 1, 128)*.02)
        self.critic_pool = nn.MultiheadAttention(128, 4, batch_first=True, dropout=0)
        self.critic_pool_norm = nn.LayerNorm(128)
        self.critic_pool_ff = nn.Sequential(nn.Linear(128, 256), nn.GELU(), nn.Linear(256, 128))
        self.critic_pool_final = nn.LayerNorm(128)
        self.value_head = nn.Sequential(nn.Linear(128, 128), nn.GELU(), nn.Linear(128, 1))
