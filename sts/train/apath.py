"""A路径on-policy PPO、全局shuffle与活动环境重放恢复。"""
import copy
import hashlib
import json
import pickle
import random
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from sts.battle_reward_v2 import contract as reward_contract
from sts.env.apath import APathEnv, load_pool, sample_scene, canonical
from sts.env.entities import CONTRACT
from sts.env.lightspeed import _load_backend
from sts.models.apath import APathActorCritic, batch_samples, encode
from sts.train.ppo import compute_gae, ppo_loss


def fingerprint():
    root=Path(__file__).parents[2]
    paths=['sts/env/relic_card_state.py','sts/env/relic_state.py','sts/env/relic-state-registry.json','sts/env/relics.py','patches/lightspeed-relic-state.patch','sts/battle_reward_v2.py','sts/train/apath.py','sts/models/apath.py','sts/models/entities.py','sts/env/apath.py',
           'sts/env/a-path-training-pool.json','sts/env/entities.py','sts/env/ironclad.py',
           'sts/env/full_card_public.py','sts/env/selection.py','sts/train/ppo.py',
           'sts/env/ironclad-expansion-contract.json','sts/env/ironclad-registry.json',
           'sts/models/unified-entity-contract.json','scripts/run-a-path-ppo.py','eval_seeds.json']
    return {**{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
            'backend':hashlib.sha256(Path(_load_backend().__file__).read_bytes()).hexdigest()}


def plain_route(route):
    return {k:v for k,v in route.items() if k not in {'snapshot','decision_id'}}


def bind_route(route, obs):
    if route['kind']=='NORMAL':
        return {**route,'snapshot':obs['routing']['snapshot']}
    return {**route,'decision_id':obs['decision']['routing']['decision_id']}


def sample_digest(sample):
    raw=sample.entities
    semantic=dict(tokens=[(t.entity_type,t.features.tolist()) for t in raw.tokens],
        candidates=[(c.kind,c.source,c.target,c.legal,c.context) for c in raw.candidates],
        held=raw.held_card_index.tolist(),routes=[plain_route(r) for r in raw.routes],context=sample.context.tolist())
    return hashlib.sha256(canonical(semantic)).hexdigest()


def check_deadline(deadline):
    if deadline is not None and time.monotonic()>=deadline:
        raise TimeoutError('达到本轮时间预算')


class APathTrainer:
    def __init__(self, group=0, device='cpu', num_envs=8, num_steps=128, total_transitions=262144):
        if num_envs*num_steps<2 or total_transitions%(num_envs*num_steps):
            raise ValueError('预算必须整除完整rollout且至少两个样本')
        self.config=dict(group=group,device=device,num_envs=num_envs,num_steps=num_steps,total_transitions=total_transitions)
        self.device=torch.device(device)
        self.scene_rng=np.random.default_rng(831000+group)
        self.environment_rng=np.random.default_rng(832000+group)
        self.shuffle_rng=np.random.default_rng(833000+group)
        self.used_seeds=set()
        torch.manual_seed(834000+group)
        self.model=APathActorCritic().to(self.device)
        self.action_rng=torch.Generator(device=self.device).manual_seed(835000+group)
        self.optimizer=torch.optim.Adam(self.model.parameters(),lr=2.5e-4,eps=1e-5)
        self.iteration,self.env_steps,self.phase=0,0,'idle'
        self.envs=[APathEnv() for _ in range(num_envs)]
        self.active=[None]*num_envs
        self.observations=[self.reset(i) for i in range(num_envs)]
        self.last_rollout=None
        self.pending_rollout=None

    def reset(self,i):
        registered=sample_scene(self.scene_rng)
        while True:
            seed=int(self.environment_rng.integers(10**12,2**63-1))
            if seed not in self.used_seeds:
                break
        self.used_seeds.add(seed)
        self.active[i]=dict(scene=registered,seed=seed,actions=[],return_observed=0.,potion_uses=0,steps=0)
        return encode(self.envs[i].reset(registered,seed,purpose='train'))

    def collect(self,deadline=None):
        self.phase='collect'; started=time.monotonic()
        t,n=self.config['num_steps'],self.config['num_envs']
        samples,labels=[],[]
        u,j=torch.empty(t,n,dtype=torch.long),torch.empty(t,n,dtype=torch.long)
        logs,values,rewards,nextvalues=[torch.zeros(t,n) for _ in range(4)]
        terms,truncs=torch.zeros(t,n,dtype=torch.bool),torch.zeros(t,n,dtype=torch.bool)
        episodes=[];diagnostics=defaultdict(lambda:defaultdict(list))
        self.model.eval()
        for step in range(t):
            check_deadline(deadline)
            current=self.observations
            samples.extend(current)
            labels.extend(a['scene']['content_group'] for a in self.active)
            with torch.no_grad():
                dist,value=self.model(batch_samples(current,self.device))
                sources,targets=dist.sample(self.action_rng)
                log=dist.log_prob(sources,targets)
                ent=dist.entropy().cpu().tolist()
                h_source=(-(dist.source_probs*dist.source_logp).sum(-1)).cpu().tolist()
            u[step],j[step],logs[step],values[step]=sources.cpu(),targets.cpu(),log.cpu(),value.cpu()
            for i in range(n):
                active=self.active[i]; label=active['scene']['content_group']
                diagnostics[label]['entropy'].append(ent[i]); diagnostics[label]['source_entropy'].append(h_source[i])
                diagnostics[label]['conditional_target_entropy'].append(ent[i]-h_source[i])
                diagnostics[label]['value'].append(values[step,i].item())
                diagnostics[label]['entities'].append(len(current[i].entities.tokens))
                diagnostics[label]['legal_actions'].append(sum(map(len,current[i].routes)))
                route=current[i].route(int(u[step,i]),int(j[step,i]))
                obs,reward,term,trunc,info=self.envs[i].step(route)
                self.env_steps+=1
                active['actions'].append(plain_route(route));active['steps']+=1;active['return_observed']+=reward
                active['potion_uses']=info['reward_accounting']['potion_uses']
                nxt=encode(obs)
                rewards[step,i],terms[step,i],truncs[step,i]=reward,term,trunc
                if trunc:
                    with torch.no_grad():
                        nextvalues[step,i]=self.model.value_only(batch_samples([nxt],self.device)).cpu()[0]
                if term or trunc:
                    episodes.append(dict(group=label,source_group=active['scene']['component_id'],
                        content_id=active['scene']['content_id'],condition=active['scene']['condition'],
                        encounter=active['scene']['encounter'],seed=active['seed'],steps=active['steps'],
                        return_observed=active['return_observed'],return_complete=active['return_observed'] if term else None,
                        terminated=term,truncated=trunc,outcome=info['task_outcome'],hp=obs['player']['hp'],
                        max_hp=obs['player']['max_hp'],potion_uses=active['potion_uses'],reason=info['termination_reason'],
                        reward_contract=info['reward_contract'],reward_accounting=info['reward_accounting']))
                    self.observations[i]=self.reset(i)
                else:
                    self.observations[i]=nxt
        ends=terms|truncs
        nextvalues[:-1]=torch.where(ends[:-1],nextvalues[:-1],values[1:])
        with torch.no_grad():
            final=self.model.value_only(batch_samples(self.observations,self.device)).cpu()
        nextvalues[-1]=torch.where(ends[-1],nextvalues[-1],final)
        advantages,returns=compute_gae(rewards,values,nextvalues,terms,truncated=truncs,
                                       episode_ends=ends,gamma=1.,gae_lambda=.95)
        rollout=dict(samples=samples,labels=labels,source=u.flatten(),target=j.flatten(),old_logp=logs.flatten(),
            old_value=values.flatten(),advantage=advantages.flatten(),returns=returns.flatten(),
            rewards=rewards,terminated=terms,truncated=truncs,next_values=nextvalues)
        # 不可变序列化轨迹同时是checkpoint证据，PPO不查询活动环境。
        raw=pickle.dumps(rollout,protocol=5)
        self.pending_rollout=raw
        summaries={g:{k:float(np.mean(v)) for k,v in d.items()} for g,d in diagnostics.items()}
        return rollout,episodes,summaries,time.monotonic()-started

    def update(self,rollout,deadline=None):
        self.phase='update';started=time.monotonic();self.model.train()
        size=len(rollout['samples'])
        lr=2.5e-4*(1-self.iteration*size/self.config['total_transitions'])
        self.optimizer.param_groups[0]['lr']=lr
        metrics=[];by_group=defaultdict(lambda:defaultdict(list))
        for epoch in range(4):
            order=self.shuffle_rng.permutation(size)
            for start in range(0,size,64):
                check_deadline(deadline)
                selected=order[start:start+64].tolist()
                adv=rollout['advantage'][selected]
                normalized=(adv-adv.mean())/(adv.std()+1e-8) if len(selected)>1 else adv
                norm_by_index=dict(zip(selected,normalized.tolist()))
                # 只在同一随机逻辑minibatch内按长度排序拆微批，不换样本、不设组配额。
                selected.sort(key=lambda i:len(rollout['samples'][i].entities.tokens))
                self.optimizer.zero_grad(set_to_none=True)
                cursor=0
                while cursor<len(selected):
                    count=min(64,len(selected)-cursor)
                    while count>1:
                        length=max(len(rollout['samples'][i].entities.tokens) for i in selected[cursor:cursor+count])
                        if count*4*length*length<=CONTRACT['resources']['max_attention_elements']:
                            break
                        count=max(1,count//2)
                    indices=selected[cursor:cursor+count];cursor+=count
                    batch=batch_samples([rollout['samples'][i] for i in indices],self.device)
                    src=rollout['source'][indices].to(self.device);tgt=rollout['target'][indices].to(self.device)
                    logp,entropy,value=self.model.evaluate_actions(batch,src,tgt)
                    oldlog,oldvalue,returns=[rollout[k][indices].to(self.device) for k in ('old_logp','old_value','returns')]
                    advantage=torch.tensor([norm_by_index[i] for i in indices],device=self.device)
                    loss,stats=ppo_loss(logp,oldlog,advantage,value,oldvalue,returns,entropy,norm_adv=False,
                                        clip_coef=.2,ent_coef=.01,vf_coef=.5)
                    if not torch.isfinite(loss):
                        raise FloatingPointError('非有限PPO loss')
                    (loss*len(indices)/len(selected)).backward()
                    metrics.append({k:float(v) for k,v in stats.items()})
                    with torch.no_grad():
                        ratio=(logp-oldlog).exp()
                        errors=(value-returns).cpu().numpy()
                        entropy_values=entropy.cpu().numpy()
                        kls=(ratio-1-(logp-oldlog)).cpu().numpy()
                        clips=((ratio-1).abs()>.2).cpu().numpy()
                        for k,index in enumerate(indices):
                            d=by_group[rollout['labels'][index]]
                            d['value_mse'].append(float(errors[k]**2))
                            d['value_bias'].append(float(errors[k]))
                            d['entropy'].append(float(entropy_values[k]))
                            d['approx_kl'].append(float(kls[k]))
                            d['clip_fraction'].append(float(clips[k]))
                grad=torch.nn.utils.clip_grad_norm_(self.model.parameters(),.5,error_if_nonfinite=True)
                self.optimizer.step()
        self.iteration+=1;self.phase='idle'
        self.last_rollout=self.pending_rollout;self.pending_rollout=None
        return dict(learning_rate=lr,grad_norm=float(grad),update_seconds=time.monotonic()-started,
            **{k:float(np.mean([m[k] for m in metrics])) for k in metrics[0]},
            group_updates={g:{k:float(np.mean(v)) for k,v in d.items()} for g,d in by_group.items()})

    def iteration_step(self,deadline=None):
        size=self.config['num_envs']*self.config['num_steps']
        if self.env_steps+size>self.config['total_transitions']:
            raise ValueError('已达到固定transition预算')
        rollout,episodes,groups,seconds=self.collect(deadline)
        metrics=self.update(rollout,deadline)
        for group in groups:
            idx=[i for i,g in enumerate(rollout['labels']) if g==group]
            ret=rollout['returns'][idx];old=rollout['old_value'][idx];variance=float(ret.var(unbiased=False))
            groups[group].update(transitions=len(idx),return_target=float(ret.mean()),
                explained_variance=1-float((ret-old).var(unbiased=False))/variance if variance>0 else None)
        metrics.update(iteration=self.iteration,env_steps=self.env_steps,collect_seconds=seconds,groups=groups)
        return metrics,episodes

    def save(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        state=dict(schema='a-path-ppo-checkpoint-v1',config=self.config,iteration=self.iteration,env_steps=self.env_steps,
            phase=self.phase,resume_allowed=self.phase=='idle',model=self.model.state_dict(),optimizer=self.optimizer.state_dict(),
            scene_rng=self.scene_rng.bit_generator.state,environment_rng=self.environment_rng.bit_generator.state,
            shuffle_rng=self.shuffle_rng.bit_generator.state,action_rng=self.action_rng.get_state(),
            torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all() if self.device.type=='cuda' else [],
            python_rng=random.getstate(),numpy_rng=np.random.get_state(),used_seeds=self.used_seeds,
            active=copy.deepcopy(self.active),observations=[sample_digest(s) for s in self.observations],
            last_rollout=self.last_rollout,pending_rollout=self.pending_rollout,
            last_rollout_sha256=hashlib.sha256(self.last_rollout).hexdigest() if self.last_rollout else None,
            reward_contract=reward_contract(),fingerprint=fingerprint())
        temporary=path.with_suffix(path.suffix+'.tmp');torch.save(state,temporary);temporary.replace(path)

    @classmethod
    def load(cls,path):
        state=torch.load(path,map_location='cpu',weights_only=False)
        if state.get('schema')!='a-path-ppo-checkpoint-v1' or state['fingerprint']!=fingerprint():
            raise ValueError('策略checkpoint版本/代码/后端/数据指纹不兼容')
        if state.get('reward_contract') != reward_contract():
            raise ValueError('Checkpoint reward contract is incompatible')
        if not state['resume_allowed']:
            raise ValueError('非更新边界快照仅供故障诊断，不能伪装精确续训')
        if state['last_rollout'] and hashlib.sha256(state['last_rollout']).hexdigest()!=state['last_rollout_sha256']:
            raise ValueError('不可变轨迹校验失败')
        trainer=cls(**state['config']);trainer.model.load_state_dict(state['model']);trainer.optimizer.load_state_dict(state['optimizer'])
        trainer.iteration,trainer.env_steps=state['iteration'],state['env_steps']
        trainer.active=state['active'];trainer.used_seeds=state['used_seeds'];trainer.last_rollout=state['last_rollout']
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
