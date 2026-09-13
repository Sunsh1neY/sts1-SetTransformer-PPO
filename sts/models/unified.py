"""五类实体共同注意力与动态候选匹配；路由索引不进入语义特征。"""
import copy
import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical

from sts.models.unified_fields import encode_fields, CONTRACT, PUBLIC_CONTRACT, PLAYER, HISTORY, FEATURES
from sts.env.public_battle import _canonical

PLAYER_DIM = len(PLAYER) + 2 * len(CONTRACT['player_statuses']) + 1
ENEMY_DIM = (7 + len(CONTRACT['enemy_names']) + 3 * len(CONTRACT['intent_kinds'])
             + 2 * len(CONTRACT['enemy_statuses']) + len(HISTORY))
POTION_DIM = len(PUBLIC_CONTRACT['potions']) + 4
RELIC_DIM = len(PUBLIC_CONTRACT['relics']) + 3
DIMS = [FEATURES, ENEMY_DIM, POTION_DIM, RELIC_DIM, PLAYER_DIM]
MAX_FEATURES = max(DIMS)


def encode(obs):
    """复用同源数值转换后立即拆为实体；没有全局固定拼接模型分支。"""
    # 旧公开接口把逐目标伤害按敌人槽位排列。这里只按敌人公开语义
    # 重排该关系字段，使原始槽位交换不改变卡牌token；动作仍用原始路由。
    semantic = copy.deepcopy(obs)
    enemy_order = sorted(range(len(obs['enemies'])), key=lambda i: _canonical(obs['enemies'][i]))
    for region in ('hand', 'draw_pile', 'discard_pile', 'exhaust_pile'):
        for card in semantic[region]:
            card['damage_by_target'] = [card['damage_by_target'][i] for i in enemy_order]
    base = encode_fields(semantic)
    rows, kinds, ids = [], [], []

    def add(kind, values, identity=0):
        row = np.zeros(MAX_FEATURES, np.float32)
        row[:len(values)] = values
        rows.append(row); kinds.append(kind); ids.append(identity)
        return len(rows) - 1

    card_positions = []
    for i in range(sum(len(obs[k]) for k in ('hand', 'draw_pile', 'discard_pile', 'exhaust_pile'))):
        card_positions.append(add(0, base['cards'][i], int(base['ids'][i])))
    raw, cursor = base['global'], PLAYER_DIM - 1
    player_features = np.concatenate((raw[:cursor], raw[-1:]))
    enemies = {}
    for i, enemy in enumerate(obs['enemies']):
        values = raw[cursor:cursor + ENEMY_DIM]; cursor += ENEMY_DIM
        if enemy['present']:
            enemies[i] = add(1, values)
    potions = {}
    for i, potion in enumerate(obs['potions']):
        values = raw[cursor:cursor + POTION_DIM]; cursor += POTION_DIM
        if potion['present']:
            potions[i] = add(2, values)
    for i, definition in enumerate(PUBLIC_CONTRACT['relics']):
        values = raw[cursor:cursor + 3]; cursor += 3
        if values[0]:
            identity = np.eye(len(PUBLIC_CONTRACT['relics']), dtype=np.float32)[i]
            add(3, np.concatenate((identity, values)))
    if cursor != len(raw) - 1:
        raise ValueError('实体字段切分未完整覆盖公开观测')
    player = add(4, player_features)
    sources = np.full(66, player, dtype=np.int64)
    targets = np.full(66, -1, dtype=np.int64)
    action_types = np.zeros(66, np.int64)
    for slot, card in enumerate(obs['hand']):
        for target in range(5):
            a = slot * 5 + target
            sources[a] = card_positions[slot]
            if card['target_kind'] == 'ENEMY':
                targets[a] = enemies.get(target, -1)
    action_types[50] = 1
    for slot, potion in enumerate(obs['potions']):
        for target in range(5):
            a = 51 + slot * 5 + target
            action_types[a] = 2
            sources[a] = potions.get(slot, player)
            if potion['target_kind'] == 'ENEMY':
                targets[a] = enemies.get(target, -1)
    return dict(features=np.stack(rows), kinds=np.array(kinds, np.int64), ids=np.array(ids, np.int64),
                valid=np.ones(len(rows), bool), sources=sources, targets=targets,
                action_types=action_types, mask=base['mask'])


def tensor_batch(rows):
    length = max(len(r['valid']) for r in rows)
    result = {}
    for key in rows[0]:
        values = [r[key] for r in rows]
        if key in ('features', 'kinds', 'ids', 'valid'):
            values = [np.pad(v, [(0, length-len(v))] + [(0, 0)] * (v.ndim-1)) for v in values]
        result[key] = torch.from_numpy(np.stack(values))
    return result


class Attention(nn.Module):
    """手写4头QKV；只屏蔽key，padding query在模块输出清零。"""
    def __init__(self):
        super().__init__()
        self.q, self.k, self.v, self.out = [nn.Linear(64, 64) for _ in range(4)]

    def forward(self, query, keys, valid):
        def heads(x):
            return x.reshape(x.shape[0], x.shape[1], 4, 16).transpose(1, 2)
        q, k, v = heads(self.q(query)), heads(self.k(keys)), heads(self.v(keys))
        weights = ((q @ k.transpose(-1, -2)) / 4).masked_fill(~valid[:, None, None, :], -torch.inf).softmax(-1)
        mixed = (weights @ v).transpose(1, 2).reshape(query.shape[0], query.shape[1], 64)
        return self.out(mixed)


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.attention = Attention()
        self.norm1, self.norm2 = nn.LayerNorm(64), nn.LayerNorm(64)
        self.ff = nn.Sequential(nn.Linear(64, 128), nn.GELU(), nn.Linear(128, 64))

    def forward(self, x, valid):
        normalized = self.norm1(x)
        x = x + self.attention(normalized, normalized, valid)
        x = x + self.ff(self.norm2(x))
        return x * valid.unsqueeze(-1)


class UnifiedActorCritic(nn.Module):
    def __init__(self, kind='set', global_dim=None):
        super().__init__()
        if kind != 'set':
            raise ValueError('统一实体模型仅支持Set')
        self.card_embedding = nn.Embedding(max(c['id'] for c in PUBLIC_CONTRACT['cards'])+1, 8, padding_idx=0)
        self.projections = nn.ModuleList([nn.Sequential(nn.Linear(d + (8 if i == 0 else 0), 64), nn.GELU()) for i, d in enumerate(DIMS)])
        self.type_embedding = nn.Embedding(5, 64)
        self.blocks = nn.ModuleList([Block() for _ in range(4)])
        self.final_norm = nn.LayerNorm(64)
        self.pool_seed = nn.Parameter(torch.zeros(1, 1, 64))
        self.pool_attention = Attention()
        self.pool_norm1, self.pool_norm2, self.pool_final = nn.LayerNorm(64), nn.LayerNorm(64), nn.LayerNorm(64)
        self.pool_ff = nn.Sequential(nn.Linear(64, 128), nn.GELU(), nn.Linear(128, 64))
        self.query = nn.Linear(64, 64)
        self.action_embedding = nn.Embedding(3, 16)
        self.null_target = nn.Parameter(torch.zeros(64))
        self.candidate = nn.Sequential(nn.Linear(144, 128), nn.GELU(), nn.Linear(128, 64))
        self.value_head = nn.Sequential(nn.Linear(64, 64), nn.GELU(), nn.Linear(64, 1))

    def contextual(self, batch):
        x = self.type_embedding(batch['kinds'])
        for i, (dim, projection) in enumerate(zip(DIMS, self.projections)):
            features = batch['features'][..., :dim]
            if i == 0:
                features = torch.cat((features, self.card_embedding(batch['ids'])), -1)
            x = x + projection(features) * (batch['kinds'] == i).unsqueeze(-1)
        x = x * batch['valid'].unsqueeze(-1)
        for block in self.blocks:
            x = block(x, batch['valid'])
        return self.final_norm(x) * batch['valid'].unsqueeze(-1)

    def forward(self, batch):
        x = self.contextual(batch)
        seed = self.pool_seed.expand(x.shape[0], -1, -1)
        pooled = seed + self.pool_attention(self.pool_norm1(seed), x, batch['valid'])
        pooled = pooled + self.pool_ff(self.pool_norm2(pooled))
        summary = self.pool_final(pooled[:, 0])
        rows = torch.arange(x.shape[0], device=x.device)[:, None]
        source = x[rows, batch['sources']]
        target = x[rows, batch['targets'].clamp_min(0)]
        target = torch.where((batch['targets'] < 0).unsqueeze(-1), self.null_target, target)
        candidate = self.candidate(torch.cat((self.action_embedding(batch['action_types']), source, target), -1))
        logits = (self.query(summary)[:, None] * candidate).sum(-1) / 8
        return logits, self.value_head(summary).squeeze(-1)

    def distribution(self, batch):
        logits, value = self(batch)
        mask = batch['mask'].clone()
        mask[~mask.any(1), 50] = True
        return Categorical(logits=logits.masked_fill(~mask, -torch.inf)), value
