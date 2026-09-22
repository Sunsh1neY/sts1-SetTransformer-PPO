"""M2a: independent source-context pooling and one dynamic query per task."""
import torch
from torch import nn
from sts.models.apath import APathActorCritic, JointDistribution, TASKS


class SourceContextPool(nn.Module):
    """Independent one-seed PMA, including attention, FFN and normalization."""
    def __init__(self):
        super().__init__()
        self.seed = nn.Parameter(torch.randn(1, 1, 64) * .02)
        self.attention = nn.MultiheadAttention(64, 4, batch_first=True, dropout=0)
        self.norm = nn.LayerNorm(64)
        self.ff = nn.Sequential(nn.Linear(64, 128), nn.GELU(), nn.Linear(128, 64))
        self.final = nn.LayerNorm(64)

    def forward(self, entities, valid):
        query = self.seed.expand(len(entities), -1, -1)
        pooled = query + self.attention(
            query, entities, entities, key_padding_mask=~valid, need_weights=False
        )[0]
        pooled = pooled + self.ff(self.norm(pooled))
        return self.final(pooled[:, 0])


class M2aActorCritic(APathActorCritic):
    model_version = "a-path-m2a-independent-source-context-v1"

    def __init__(self):
        # Construct unchanged modules first for same-seed initialization pairing.
        super().__init__()
        self.source_context_pool = SourceContextPool()
        self.source_query_delta = nn.Sequential(
            nn.Linear(128, 64), nn.GELU(), nn.Linear(64, 64)
        )
        # Start at exactly the M0 function, without importing trained M0 weights.
        nn.init.zeros_(self.source_query_delta[-1].weight)
        nn.init.zeros_(self.source_query_delta[-1].bias)

    def readout_logits(self, h, batch):
        """Expose raw scores to distinguish head isolation from softmax coupling."""
        b, u, j = batch["target_index"].shape
        end_context = self._pool_branch(h, batch["entity_valid"])
        context = self.source_context_pool(h, batch["entity_valid"])
        source = h.gather(1, batch["source_index"][..., None].expand(-1, -1, 64))
        task_query = self.task_query(batch["task"])
        delta = self.source_query_delta(torch.cat(
            [task_query, context[:, None].expand(-1, u, -1)], dim=-1
        ))
        logits = ((task_query + delta) * self.source_key(source)).sum(-1) / 8
        logits = torch.where(
            batch["task"] == TASKS.index("END_TURN"),
            self.special(end_context).expand(-1, u), logits
        )
        idx = batch["target_index"]
        target = h.gather(
            1, idx.clamp_min(0).reshape(b, -1)[..., None].expand(-1, -1, 64)
        ).reshape(b, u, j, 64)
        target_logits = (
            self.target_query(source)[:, :, None] * self.target_key(target)
        ).sum(-1) / 8
        return logits, target_logits.masked_fill(idx < 0, 0)

    def forward(self, batch):
        h, critic_context = self.encode_entities(batch)
        source_logits, target_logits = self.readout_logits(h, batch)
        return JointDistribution(
            source_logits, target_logits, batch["source_mask"], batch["target_mask"]
        ), self.value_head(critic_context).squeeze(-1)
