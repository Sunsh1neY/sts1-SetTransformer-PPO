"""随机策略基线（周 2 出口：随机策略能打完一场）。

动作选择的随机性来自 Python 标准库 random（agent 自己的种子），与环境的
4 条 Java 流**完全隔离**（D14：numpy 已退出环境内使用；环境可复现性只依赖
combat seed，agent seed 只决定走哪条轨迹）。
"""

import random

from sts.env.combat import Combat


class RandomAgent:
    def __init__(self, seed: int = 0):
        self.seed = seed
        self._rng = random.Random(seed)

    def act(self, env: Combat) -> int:
        """从环境给出的合法动作列表里均匀随机挑一个（合法动作率恒 0 违规）。"""
        legal = env.legal_actions()
        return legal[self._rng.randrange(len(legal))]

    def run_episode(self, env: Combat) -> dict:
        """打完一场，返回简要统计。env 需已 reset。"""
        steps = 0
        while not env.done:
            env.step(self.act(env))
            steps += 1
        return {
            "steps": steps,
            "won": env.won,
            "turns": env.state.turn,
            "player_hp": max(0, env.state.player.hp),
        }
