"""战斗状态（spec-v4 §11：避免深拷贝；第 4 周性能优化时再收紧）。

手牌为 ID 列表，**列表下标即槽位**：抽牌 append（槽位按抽牌顺序分配，§0 关键约定），
打出 pop 后余牌左移——同一 seed + 同一动作序列下槽位分配确定，replay 对拍才成立。
"""

from dataclasses import dataclass, field

from sts.env.rng import CombatRNG


@dataclass
class PlayerState:
    hp: int = 80
    hp_max: int = 80
    block: int = 0
    energy: int = 3
    strength: int = 0
    vulnerable: int = 0  # 剩余回合数（§0）
    weak: int = 0


@dataclass
class EnemyState:
    kind: str  # jaw_worm | cultist | louse_red | louse_green
    name: str
    hp: int
    hp_max: int
    block: int = 0
    strength: int = 0
    vulnerable: int = 0
    weak: int = 0
    ritual: bool = False  # Cultist Incantation：每回合结束力量 +3（§7）
    ritual_skip_first: bool = False  # RitualPower skipFirst：施放当回合结束不触发（对拍收口）
    intent: str | None = None
    # 行动历史（h[0] = 最近一次，对拍 lastMove / lastTwoMoves 约束用）
    move_history: list[str] = field(default_factory=list)
    # Louse 专用（§7）：咬伤定值每场开局 roll 一次全程不变；
    # Curl Up 格挡量 init 时 roll（对拍收口），受击首次启用，每场一次
    bite_damage: int | None = None
    curl_up_block: int = 0
    curl_up_used: bool = False

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass
class CombatState:
    player: PlayerState
    enemies: list[EnemyState]
    hand: list[str] = field(default_factory=list)
    draw_pile: list[str] = field(default_factory=list)  # 列表尾 = 牌库顶
    discard_pile: list[str] = field(default_factory=list)
    turn: int = 1
    phase: str = "player"  # player | won | lost（§3 X）
    rng: CombatRNG | None = None

    def signature(self) -> tuple:
        """可复现性断言用的全量状态指纹（T18/T19）：同 seed 同动作 → 逐步相同。"""
        return (
            self.turn,
            self.phase,
            (self.player.hp, self.player.block, self.player.energy,
             self.player.strength, self.player.vulnerable, self.player.weak),
            tuple(
                (e.kind, e.hp, e.block, e.strength, e.vulnerable, e.weak,
                 e.ritual, e.intent, e.bite_damage, e.curl_up_block,
                 e.curl_up_used, tuple(e.move_history))
                for e in self.enemies
            ),
            tuple(self.hand),
            tuple(self.draw_pile),
            tuple(self.discard_pile),
            tuple(sorted(self.rng.consumption().items())) if self.rng else None,
        )
