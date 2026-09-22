"""M2a adapter retaining the frozen M0 PPO implementation."""
import hashlib
import copy
import random
import numpy as np
from pathlib import Path
import torch
from sts.train.apath import APathTrainer as M0Trainer, fingerprint as m0_fingerprint, check_deadline
from sts.train.apath import sample_digest
from sts.battle_reward_v2 import contract as reward_contract
from sts.models.architectures.m2a_source_context.model import M2aActorCritic

def fingerprint(corpus_dir=None):
    result = m0_fingerprint(corpus_dir)
    root = Path(__file__).resolve().parents[2]
    paths = ["sts/train/m2a.py", "scripts/run-m2a-corpus-ppo.py",
             "sts/models/architectures/__init__.py",
             "sts/models/architectures/m2a_source_context/__init__.py",
             "sts/models/architectures/m2a_source_context/model.py",
             "sts/models/architectures/README.md"]
    for path in paths:
        result[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    return result

class APathTrainer(M0Trainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        torch.manual_seed(834000 + self.config["group"])
        self.model = M2aActorCritic().to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=2.5e-4, eps=1e-5)

    def save(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        state=dict(schema='m2a-ppo-checkpoint-v1',model_version=self.model.model_version,config=self.config,iteration=self.iteration,env_steps=self.env_steps,
            phase=self.phase,resume_allowed=False,model=self.model.state_dict(),optimizer=self.optimizer.state_dict(),
            scene_rng=self.scene_rng.bit_generator.state,environment_rng=self.environment_rng.bit_generator.state,
            shuffle_rng=self.shuffle_rng.bit_generator.state,action_rng=self.action_rng.get_state(),
            torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all() if self.device.type=='cuda' else [],
            python_rng=random.getstate(),numpy_rng=np.random.get_state(),used_seeds=self.used_seeds,
            active=copy.deepcopy(self.active),observations=[sample_digest(s) for s in self.observations],
            last_rollout=self.last_rollout,pending_rollout=self.pending_rollout,
            last_rollout_sha256=hashlib.sha256(self.last_rollout).hexdigest() if self.last_rollout else None,
            reset_counts=dict(self.reset_counts), reward_contract=reward_contract(),fingerprint=fingerprint(self.config.get('corpus_dir')))
        temporary=path.with_suffix(path.suffix+'.tmp');torch.save(state,temporary);temporary.replace(path)


    @classmethod
    def load(cls, path):
        raise ValueError("M2a resume is not implemented; do not load through the M0 trainer.")
