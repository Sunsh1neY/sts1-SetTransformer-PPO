"""Four independent private critic SAB blocks; total critic SAB path depth six."""
from sts.models.entities import EntityArchitecture, EntityBlock
from ..critic_common import CriticVariant

class CD4ActorCritic(CriticVariant):
    model_version = "a-path-critic-depth4-v1"
    def __init__(self):
        super().__init__()
        self.critic_blocks.extend([EntityBlock(EntityArchitecture()) for _ in range(2)])
