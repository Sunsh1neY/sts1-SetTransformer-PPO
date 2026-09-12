"""全类型实体共同参与注意力的Set Actor-Critic；无槽位或位置编码。"""
from dataclasses import asdict, dataclass

import torch
from torch import nn
from torch.distributions import Categorical

from sts.env.entities import CANDIDATE_CONTEXT_DIM, CONTRACT, FEATURE_DIMS, KINDS, TYPES


@dataclass(frozen=True)
class EntityArchitecture:
    width: int = 64
    heads: int = 4
    layers: int = 2
    ff_width: int = 128
    dropout: float = 0.0

    def validate(self):
        if any(type(v) is not int or v < 1 for v in (self.width, self.heads, self.layers, self.ff_width)):
            raise ValueError("模型尺寸必须为正整数")
        if self.width % self.heads or self.dropout != 0:
            raise ValueError("宽度须整除头数；当前恢复契约只批准dropout=0")


class EntityBlock(nn.Module):
    """pre-LN多头注意力、双残差及逐token前馈；无伤害预览。"""

    def __init__(self, config):
        super().__init__()
        w = config.width
        self.heads, self.width = config.heads, w
        self.norm1, self.norm2 = nn.LayerNorm(w), nn.LayerNorm(w)
        self.qkv = nn.Linear(w, 3 * w)
        self.output = nn.Linear(w, w)
        self.ff = nn.Sequential(nn.Linear(w, config.ff_width), nn.GELU(), nn.Linear(config.ff_width, w))

    def forward(self, x, valid):
        b, n, w = x.shape
        qkv = self.qkv(self.norm1(x)).reshape(b, n, 3, self.heads, w // self.heads)
        q, k, v = qkv.permute(2, 0, 3, 1, 4).unbind(0)
        logits = q @ k.transpose(-1, -2) / (w // self.heads) ** 0.5
        logits = logits.masked_fill(~valid[:, None, None, :], -torch.inf)
        attended = (logits.softmax(-1) @ v).transpose(1, 2).reshape(b, n, w)
        x = x + self.output(attended)
        x = x + self.ff(self.norm2(x))
        return x.masked_fill(~valid[..., None], 0)


class UnifiedEntityActorCritic(nn.Module):
    model_version = "unified-entity-set-v4"

    def __init__(self, architecture=None):
        super().__init__()
        self.architecture = EntityArchitecture(**(architecture or CONTRACT["architecture"]))
        self.architecture.validate()
        w = self.architecture.width
        self.projections = nn.ModuleDict({kind: nn.Linear(dim, w) for kind, dim in FEATURE_DIMS.items()})
        self.type_embedding = nn.Embedding(len(TYPES), w)
        self.blocks = nn.ModuleList([EntityBlock(self.architecture) for _ in range(self.architecture.layers)])
        self.final_norm = nn.LayerNorm(w)
        self.action_embedding = nn.Embedding(len(KINDS), 8)
        self.action_head = nn.Sequential(nn.Linear(3 * w + 10 + CANDIDATE_CONTEXT_DIM, w), nn.GELU(), nn.Linear(w, 1))
        self.value_head = nn.Sequential(nn.Linear(w + CANDIDATE_CONTEXT_DIM, w), nn.GELU(), nn.Linear(w, 1))

    def encode_entities(self, batch):
        valid = batch["entity_valid"]
        b, n = valid.shape
        resources = CONTRACT["resources"]
        if not valid.any(1).all():
            raise ValueError("每个样本至少需要玩家实体")
        if n > resources["max_entities"] or b * self.architecture.heads * n * n > resources["max_attention_elements"]:
            raise ValueError("注意力资源边界超限")
        types = batch["types"].masked_fill(~valid, 0)
        x = self.type_embedding(types).masked_fill(~valid[..., None], 0)
        for i, kind in enumerate(TYPES):
            selected = valid & (types == i)
            # 先清除非本类型及padding输入，避免无效位置数值影响投影。
            features = batch["features"][kind].masked_fill(~selected[..., None], 0)
            x = x + self.projections[kind](features).masked_fill(~selected[..., None], 0)
        for block in self.blocks:
            x = block(x, valid)
        x = self.final_norm(x).masked_fill(~valid[..., None], 0)
        context = x.sum(1) / valid.sum(1, keepdim=True)
        return x, context

    def forward(self, batch):
        x, context = self.encode_entities(batch)
        b, a = batch["source"].shape
        if a > CONTRACT["resources"]["max_candidates"]:
            raise ValueError("候选资源边界超限")
        width = x.shape[-1]

        def gather(index):
            values = x.gather(1, index.clamp_min(0)[..., None].expand(-1, -1, width))
            return values.masked_fill((index < 0)[..., None], 0)

        source, target = batch["source"], batch["target"]
        features = torch.cat([gather(source), gather(target), context[:, None].expand(-1, a, -1),
                               self.action_embedding(batch["kinds"]),
                               (source >= 0).float()[..., None], (target >= 0).float()[..., None],
                               batch["candidate_context"]], -1)
        scores = self.action_head(features).squeeze(-1)
        mask = batch["candidate_valid"] & batch["legal"]
        # 当前同一选择的上下文一致；只汇总有效候选，避免padding和候选数量改变价值。
        valid = batch["candidate_valid"]
        public_context = batch["candidate_context"].masked_fill(~valid[..., None], 0).sum(1)
        public_context = public_context / valid.sum(1, keepdim=True).clamp_min(1)
        value_features = torch.cat([context, public_context], -1)
        return scores.masked_fill(~mask, -torch.inf), self.value_head(value_features).squeeze(-1)

    def distribution(self, batch):
        if not (batch["candidate_valid"] & batch["legal"]).any(1).all():
            raise ValueError("无合法动作的终局只能计算value，不能采样")
        logits, value = self(batch)
        return Categorical(logits=logits), value

    def configuration(self):
        return asdict(self.architecture)
