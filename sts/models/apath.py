"""A路径：共享实体编码、PMA和显式来源/条件敌人分布。"""
from dataclasses import dataclass
import copy

import numpy as np
import torch
from torch import nn

from sts.env.entities import (CONTRACT, TYPES, FEATURE_DIMS, CANDIDATE_CONTEXT_DIM,
                              EntitySample, collate, encode_observation)
from sts.models.entities import EntityArchitecture, EntityBlock

from sts.env.relic_state import DIMENSION as RELIC_DIM, relic_features

FEATURE_DIMS = {**FEATURE_DIMS, "RELIC": RELIC_DIM}
VERSION = "a-path-four-sab-pma-pointer-relic-v2"
TASKS = ("PLAY", "POTION", "ARMAMENTS", "DUAL_WIELD", "EXHAUST_ONE", "EXHUME", "HEADBUTT", "WARCRY", "DISCOVERY", "END_TURN")


@dataclass
class ActionSample:
    entities: EntitySample
    sources: list[int]
    tasks: list[int]
    targets: list[list[int]]
    routes: list[list]
    complete_indices: list[list[int]]
    context: np.ndarray

    def route(self, source, target):
        return copy.deepcopy(self.routes[source][target])

    def decompose(self, route):
        found = [(u, j) for u, rows in enumerate(self.routes) for j, r in enumerate(rows) if r == route]
        if len(found) != 1:
            raise ValueError("完整动作必须唯一对应来源和目标")
        return found[0]


def adapt(sample):
    """保留环境候选来源；SELECT_CARD的旧target是效果来源，不是敌人目标。"""
    if len(sample.candidates) != len(sample.routes):
        raise ValueError("候选与路由必须等长")
    groups, sources, tasks, targets, routes, complete = {}, [], [], [], [], []
    player = next(t for t in sample.tokens if t.entity_type == "PLAYER_GLOBAL")
    selection_start = len(CONTRACT["player_numeric_scales"]) + 2 * len(CONTRACT["player_statuses"]) + 3
    selection = CONTRACT["selection_kinds"][int(np.argmax(player.features[selection_start:selection_start + len(CONTRACT["selection_kinds"])]))]
    contexts = {tuple(c.context) for c in sample.candidates}
    if len(contexts) > 1:
        raise ValueError("当前公开结算上下文必须在同一状态一致")
    context = np.array(next(iter(contexts), (0.,) * CANDIDATE_CONTEXT_DIM), dtype=np.float32)
    for index, (c, route) in enumerate(zip(sample.candidates, sample.routes)):
        if not c.legal:
            continue
        task = "PLAY" if c.kind.startswith("PLAY") else "POTION" if c.kind.startswith("POTION") else selection if c.kind == "SELECT_CARD" else c.kind
        if task not in TASKS:
            raise ValueError("操作未登记，不能自动代选")
        key = (task, c.source, c.kind)
        if key not in groups:
            groups[key] = len(sources); sources.append(c.source); tasks.append(TASKS.index(task))
            targets.append([]); routes.append([]); complete.append([])
        u = groups[key]
        target = c.target if c.kind.endswith("TARGET") else -1
        if target in targets[u] or (-1 in targets[u]) or (target == -1 and targets[u]):
            raise ValueError("来源动作分解不唯一")
        targets[u].append(target); routes[u].append(copy.deepcopy(route)); complete[u].append(index)
    flat_routes = [r for row in routes for r in row]
    if any(r in flat_routes[:i] for i, r in enumerate(flat_routes)):
        raise ValueError("完整动作路由重复")
    return ActionSample(copy.deepcopy(sample), sources, tasks, targets, routes, complete, context)


def encode(obs):
    return adapt(encode_observation(obs, relic_encoder=relic_features, feature_dims=FEATURE_DIMS))


def batch_samples(samples, device="cpu"):
    # 终局也有玩家实体；空候选保留独立Value-only路径。
    entities = [s.entities for s in samples]
    batch = collate(entities, allow_empty_candidates=True, feature_dims=FEATURE_DIMS)
    b = len(samples); u = max(1, max(len(s.sources) for s in samples))
    j = max(1, max((len(t) for s in samples for t in s.targets), default=1))
    batch.update(source_index=torch.zeros(b, u, dtype=torch.long), task=torch.zeros(b, u, dtype=torch.long),
                 source_mask=torch.zeros(b, u, dtype=torch.bool), target_index=torch.full((b, u, j), -1, dtype=torch.long),
                 target_mask=torch.zeros(b, u, j, dtype=torch.bool), public_context=torch.tensor(np.stack([s.context for s in samples])))
    for i,s in enumerate(samples):
        n=len(s.sources)
        batch["source_index"][i,:n]=torch.tensor(s.sources,dtype=torch.long)
        batch["task"][i,:n]=torch.tensor(s.tasks,dtype=torch.long)
        batch["source_mask"][i,:n]=True
        for k,t in enumerate(s.targets):
            batch["target_index"][i,k,:len(t)]=torch.tensor(t)
            batch["target_mask"][i,k,:len(t)]=True
    def move(v):return {k:move(x) for k,x in v.items()} if isinstance(v,dict) else v.to(device)
    return move(batch)


def masked_logprobs(logits, mask):
    """空行仅用于padding/Value-only：安全计算，返回全零概率。"""
    live=mask.any(-1,keepdim=True)
    safe=mask | (~live & (torch.arange(mask.shape[-1],device=mask.device)==0))
    logp=logits.masked_fill(~mask,0).masked_fill(~safe,-torch.inf).log_softmax(-1)
    logp=logp.masked_fill(~mask,0)
    return logp, logp.exp().masked_fill(~mask,0)


class JointDistribution:
    def __init__(self, source_logits, target_logits, source_mask, target_mask):
        if source_mask.dtype != torch.bool or target_mask.dtype != torch.bool:
            raise ValueError("概率掩码必须为布尔类型")
        if (source_logits.shape != source_mask.shape or target_logits.shape != target_mask.shape
                or source_mask.ndim != 2 or target_mask.ndim != 3
                or source_mask.shape != target_mask.shape[:2]):
            raise ValueError("来源和目标形状不匹配")
        if not torch.equal(source_mask, target_mask.any(-1)):
            raise ValueError("合法来源必须且只能带合法条件分支")
        if not (torch.isfinite(source_logits[source_mask]).all()
                and torch.isfinite(target_logits[target_mask]).all()):
            raise ValueError("合法logit必须有限")
        self.source_mask,self.target_mask=source_mask,target_mask
        self.source_logp,self.source_probs=masked_logprobs(source_logits,source_mask)
        self.target_logp,self.target_probs=masked_logprobs(target_logits,target_mask)

    def sample(self, generator):
        if not self.source_mask.any(-1).all():raise ValueError("无合法动作，只允许Value-only")
        u=torch.multinomial(self.source_probs,1,generator=generator).squeeze(-1)
        rows=torch.arange(len(u),device=u.device)
        j=torch.multinomial(self.target_probs[rows,u],1,generator=generator).squeeze(-1)
        return u,j

    def log_prob(self, u, j):
        if u.shape != self.source_mask.shape[:1] or j.shape != u.shape:raise ValueError("动作分解须为[B]")
        rows=torch.arange(len(u),device=u.device)
        if (u<0).any() or (u>=self.source_mask.shape[1]).any() or (j<0).any() or (j>=self.target_mask.shape[2]).any():raise ValueError("历史动作越界")
        if not (self.source_mask[rows,u]&self.target_mask[rows,u,j]).all():raise ValueError("历史动作不合法")
        return self.source_logp[rows,u]+self.target_logp[rows,u,j]

    def entropy(self):
        source=-(self.source_probs*self.source_logp).sum(-1)
        target=-(self.target_probs*self.target_logp).sum(-1)
        return source+(self.source_probs*target).sum(-1)

    @property
    def probs(self):return self.source_probs[...,None]*self.target_probs

    def sequential_greedy(self):
        if not self.source_mask.any(-1).all():
            raise ValueError("无合法动作，只允许Value-only")
        u = self.source_probs.argmax(-1)
        j = self.target_probs[torch.arange(len(u), device=u.device), u].argmax(-1)
        return u, j

    def joint_map(self):
        if not self.source_mask.any(-1).all():
            raise ValueError("无合法动作，只允许Value-only")
        index = self.probs.flatten(1).argmax(-1)
        return index // self.probs.shape[-1], index % self.probs.shape[-1]


class APathActorCritic(nn.Module):
    model_version=VERSION

    def __init__(self):
        super().__init__();w=64
        self.projections=nn.ModuleDict({k:nn.Linear(v+(CANDIDATE_CONTEXT_DIM if k=="PLAYER_GLOBAL" else 0),w) for k,v in FEATURE_DIMS.items()})
        self.type_embedding=nn.Embedding(len(TYPES),w)
        self.holds_fusion=nn.Linear(w+1,w,bias=False);nn.init.zeros_(self.holds_fusion.weight)
        self.blocks=nn.ModuleList([EntityBlock(EntityArchitecture(layers=4)) for _ in range(4)])
        self.final_norm=nn.LayerNorm(w)
        self.pool_seed=nn.Parameter(torch.randn(1,1,w)*.02)
        self.pool=nn.MultiheadAttention(w,4,batch_first=True,dropout=0)
        self.pool_norm=nn.LayerNorm(w)
        self.pool_ff=nn.Sequential(nn.Linear(w,128),nn.GELU(),nn.Linear(128,w))
        self.pool_final=nn.LayerNorm(w)
        self.task_query=nn.Embedding(len(TASKS),w)
        nn.init.normal_(self.task_query.weight,std=.02)
        self.source_key=nn.Linear(w,w,bias=False)
        self.target_query=nn.Linear(w,w,bias=False)
        self.target_key=nn.Linear(w,w,bias=False)
        self.special=nn.Linear(w,1)
        self.value_head=nn.Sequential(nn.Linear(w,w),nn.GELU(),nn.Linear(w,1))

    def encode_entities(self,batch):
        valid=batch['entity_valid'];types=batch['types'].masked_fill(~valid,0)
        b, n = valid.shape
        if not valid.any(1).all():
            raise ValueError("每个样本至少需要玩家实体")
        limits = CONTRACT['resources']
        if n > limits['max_entities'] or b * 4 * n * n > limits['max_attention_elements']:
            raise ValueError("注意力资源超限，须拆分微批次，不能裁掉实体")
        x=self.type_embedding(types).masked_fill(~valid[...,None],0)
        for i,kind in enumerate(TYPES):
            selected=valid&(types==i)
            f=batch['features'][kind].masked_fill(~selected[...,None],0)
            if kind=='PLAYER_GLOBAL':f=torch.cat([f,batch['public_context'][:,None].expand(-1,f.shape[1],-1).masked_fill(~selected[...,None],0)],-1)
            x=x+self.projections[kind](f).masked_fill(~selected[...,None],0)
        held=batch['held_card_index'];mask=(held>=0)&valid
        if ((held < -1) | (held >= n)).any():
            raise ValueError("关系索引越界")
        linked_valid = valid.gather(1, held.clamp_min(0))
        linked_type = types.gather(1, held.clamp_min(0))
        if (mask & (~linked_valid | (linked_type != TYPES.index('CARD'))
                    | (types != TYPES.index('ENEMY')))).any():
            raise ValueError("关系必须从敌人指向有效扣牌实体")
        linked=x.gather(1,held.clamp_min(0)[...,None].expand(-1,-1,64)).masked_fill(~mask[...,None],0)
        x=x+self.holds_fusion(torch.cat([linked,mask.float()[...,None]],-1))
        for block in self.blocks:x=block(x,valid)
        h=self.final_norm(x).masked_fill(~valid[...,None],0)
        q=self.pool_seed.expand(len(x),-1,-1)
        pooled=q+self.pool(q,h,h,key_padding_mask=~valid,need_weights=False)[0]
        pooled=pooled+self.pool_ff(self.pool_norm(pooled))
        return h,self.pool_final(pooled[:,0])

    def forward(self,batch):
        h,g=self.encode_entities(batch);b,u,j=batch['target_index'].shape
        source=h.gather(1,batch['source_index'][...,None].expand(-1,-1,64))
        logits=(self.task_query(batch['task'])*self.source_key(source)).sum(-1)/8
        logits=torch.where(batch['task']==TASKS.index('END_TURN'),self.special(g).expand(-1,u),logits)
        idx=batch['target_index'];target=h.gather(1,idx.clamp_min(0).reshape(b,-1)[...,None].expand(-1,-1,64)).reshape(b,u,j,64)
        target_logits=(self.target_query(source)[:,:,None]*self.target_key(target)).sum(-1)/8
        target_logits=target_logits.masked_fill(idx<0,0)
        return JointDistribution(logits,target_logits,batch['source_mask'],batch['target_mask']),self.value_head(g).squeeze(-1)

    @torch.no_grad()
    def act(self,batch,generator):
        distribution,value=self(batch);u,j=distribution.sample(generator)
        return u,j,distribution.log_prob(u,j),value

    def evaluate_actions(self,batch,u,j):
        distribution,value=self(batch)
        return distribution.log_prob(u,j),distribution.entropy(),value

    def value_only(self,batch):
        return self.value_head(self.encode_entities(batch)[1]).squeeze(-1)
