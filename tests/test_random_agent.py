"""周 2 出口验收（spec-v4 §9 第 2 周）：随机策略能打完一场 + 同 seed 轨迹一致。

- 「能打完一场」：三种遭遇 × 多个 seed，全部在 max_turns 内自然终局（胜或负皆可），
  全程零非法动作（Gate 1 第 4 条的前置验证）；
- 「轨迹一致」：同 combat seed + 同 agent seed → 终局结果与逐步动作完全相同。
"""

import random as _pyrandom

from sts.agents.random_agent import RandomAgent
from sts.env.combat import Combat

ENCOUNTERS = ("jaw_worm", "cultist", "louses")


def test_随机策略三种遭遇全部能打完():
    wins = {}
    for encounter in ENCOUNTERS:
        wins[encounter] = 0
        for seed in range(20):
            env = Combat(encounter=encounter, seed=seed)
            env.reset()
            agent = RandomAgent(seed=seed + 500)
            result = agent.run_episode(env)
            assert env.done, f"{encounter} seed={seed} 未终局"
            assert result["steps"] > 0
            assert result["player_hp"] >= 0
            wins[encounter] += result["won"]
    # 随机策略胜率不是门槛，打印出来供对拍参考（Cultist 最慢、Jaw Worm 是 race）
    print({k: f"{v}/20" for k, v in wins.items()})


def test_同seed同agent_seed结果一致():
    for encounter in ENCOUNTERS:
        for seed in (3, 42):
            env_a = Combat(encounter=encounter, seed=seed)
            env_a.reset()
            env_b = Combat(encounter=encounter, seed=seed)
            env_b.reset()
            agent_a = RandomAgent(seed=77)
            agent_b = RandomAgent(seed=77)
            trace_a, trace_b = [], []
            while not env_a.done:
                move = agent_a.act(env_a)
                trace_a.append(move)
                env_a.step(move)
            while not env_b.done:
                move = agent_b.act(env_b)
                trace_b.append(move)
                env_b.step(move)
            assert trace_a == trace_b
            assert env_a.won == env_b.won
            assert env_a.state.signature() == env_b.state.signature()


def test_非法动作恒零_200步扫描():
    """随机 agent 的动作永远来自环境给出的合法列表 → 违规率恒 0（§8.5）。"""
    rng = _pyrandom.Random(0)
    env = Combat(encounter="louses", seed=99)
    env.reset()
    agent = RandomAgent(seed=1)
    for _ in range(200):
        if env.done:
            env = Combat(encounter="louses", seed=99)
            env.reset()
        legal = set(env.legal_actions())
        move = agent.act(env)
        assert move in legal
        env.step(move)
