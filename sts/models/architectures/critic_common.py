"""Shared encoder wiring for critic-only variants; frozen M0/M2a stay untouched."""
import torch
from torch import nn
from sts.models.apath import CONTRACT, TYPES
from sts.models.architectures.m2a_source_context.model import M2aActorCritic

class CriticVariant(M2aActorCritic):
    def __init__(self):
        super().__init__()
        self.critic_input = nn.Identity()

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
                    | ((types != TYPES.index('ENEMY')) & (types != TYPES.index('RELIC'))))).any():
            raise ValueError("关系必须从敌人指向有效扣牌实体")
        linked=x.gather(1,held.clamp_min(0)[...,None].expand(-1,-1,64)).masked_fill(~mask[...,None],0)
        x=x+self.holds_fusion(torch.cat([linked,mask.float()[...,None]],-1))
        for block in self.shared_blocks:x=block(x,valid)
        actor,critic=x,self.critic_input(x).masked_fill(~valid[...,None],0)
        for block in self.actor_blocks:actor=block(actor,valid)
        for block in self.critic_blocks:critic=block(critic,valid)
        h=self.final_norm(actor).masked_fill(~valid[...,None],0)
        critic=self.critic_final_norm(critic).masked_fill(~valid[...,None],0)
        return h,self._pool_branch(critic,valid,critic=True)
