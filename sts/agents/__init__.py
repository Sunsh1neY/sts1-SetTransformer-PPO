"""agents 包：随机 / 规则基线（spec-v4 §11 仓库骨架，按周生长）。"""

from sts.agents.episode_runner import Agent, EpisodeTrace, decode_agent_decision, run_episode
from sts.agents.masked_policy import AgentDecision, MaskedRandomAgent, masked_softmax

__all__ = [
    "Agent",
    "AgentDecision",
    "EpisodeTrace",
    "MaskedRandomAgent",
    "decode_agent_decision",
    "masked_softmax",
    "run_episode",
]
