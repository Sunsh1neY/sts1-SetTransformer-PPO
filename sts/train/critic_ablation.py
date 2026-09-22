"""Critic-variant trainer using unchanged M0 collector and PPO update machinery."""
import copy, hashlib, random
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from sts.train.apath import APathTrainer as BaseTrainer, sample_digest, bind_route, check_deadline
from sts.train.m2a import fingerprint as baseline_fingerprint
from sts.battle_reward_v2 import contract as reward_contract
from sts.models.apath import encode
from sts.models.architectures.critic_variants import MODELS

def fingerprint(corpus_dir=None):
    result = baseline_fingerprint(corpus_dir)
    root = Path(__file__).resolve().parents[2]
    paths = ["sts/train/critic_ablation.py", "sts/train/resource_telemetry.py", "scripts/run-critic-ablation.py",
             "sts/models/architectures/critic_common.py", "sts/models/architectures/critic_variants.py",
             "docs/critic-ablation-protocol-v1.md"]
    for folder in ("m3a_multiseed", "c_w128", "c_d4"):
        paths.extend(f"sts/models/architectures/{folder}/{file}" for file in ("__init__.py", "model.py"))
    for path in paths:
        result[path] = hashlib.sha256((root/path).read_bytes()).hexdigest()
    return result

class CriticTrainer(BaseTrainer):
    def __init__(self, architecture, **kwargs):
        if architecture not in MODELS:raise ValueError("Unknown critic architecture")
        super().__init__(**kwargs)
        self.config["architecture"] = architecture
        torch.manual_seed(834000+self.config["group"])
        self.model = MODELS[architecture]().to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=2.5e-4, eps=1e-5)

    def save(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        state=dict(schema='critic-ablation-checkpoint-v1',model_version=self.model.model_version,config=self.config,iteration=self.iteration,env_steps=self.env_steps,
            phase=self.phase,resume_allowed=self.phase=='idle',model=self.model.state_dict(),optimizer=self.optimizer.state_dict(),
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
    def load(cls,path):
        state=torch.load(path,map_location='cpu',weights_only=False)
        if state.get('schema')!='critic-ablation-checkpoint-v1' or state['fingerprint']!=fingerprint(state.get('config',{}).get('corpus_dir')):
            raise ValueError('策略checkpoint版本/代码/后端/数据指纹不兼容')
        if state.get('reward_contract') != reward_contract():
            raise ValueError('Checkpoint reward contract is incompatible')
        if not state['resume_allowed']:
            raise ValueError('非更新边界快照仅供故障诊断，不能伪装精确续训')
        if state['last_rollout'] and hashlib.sha256(state['last_rollout']).hexdigest()!=state['last_rollout_sha256']:
            raise ValueError('不可变轨迹校验失败')
        trainer=cls(**state['config'])
        if state.get('model_version') != trainer.model.model_version:raise ValueError('Architecture version mismatch')
        trainer.model.load_state_dict(state['model'],strict=True);trainer.optimizer.load_state_dict(state['optimizer'])
        trainer.iteration,trainer.env_steps=state['iteration'],state['env_steps']
        trainer.active=state['active'];trainer.used_seeds=state['used_seeds'];trainer.last_rollout=state['last_rollout']
        trainer.reset_counts=Counter(state.get('reset_counts',{}))
        trainer.observations=[]
        for env,active,expected in zip(trainer.envs,trainer.active,state['observations']):
            obs=env.reset(active['scene'],active['seed'],purpose='train')
            replay_return = 0.0
            replay_uses = 0
            for action in active['actions']:
                obs,reward,term,trunc,info=env.step(bind_route(action,obs))
                replay_return += reward
                replay_uses = info['reward_accounting']['potion_uses']
                if term or trunc:
                    raise ValueError('活动环境重放提前结束')
            if replay_return != active['return_observed'] or replay_uses != active['potion_uses']:
                raise ValueError('Replayed reward accounting disagrees with checkpoint')
            sample=encode(obs)
            if sample_digest(sample)!=expected:
                raise ValueError('重放后的公开观测或候选与checkpoint不一致')
            trainer.observations.append(sample)
        for name in ('scene_rng','environment_rng','shuffle_rng'):
            getattr(trainer,name).bit_generator.state=state[name]
        trainer.action_rng.set_state(state['action_rng']);torch.set_rng_state(state['torch_rng'])
        if state['cuda_rng']:
            torch.cuda.set_rng_state_all(state['cuda_rng'])
        random.setstate(state['python_rng']);np.random.set_state(state['numpy_rng'])
        return trainer
