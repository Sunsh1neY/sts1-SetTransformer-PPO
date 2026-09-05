"""回合结算主循环（mechanics.md §2 / §3 / §5 / §6）。

每一步的编号对应该文档的结算步骤；与日志对拍冲突时以日志为准并修订文档。
随机性全部来自 CombatRNG 的 4 条独立流（D14），流间不交叉取数；
每个随机操作的消耗次数与顺序是可复现性的一部分（Gate 1 第 3 条）。
"""

from sts.env.actions import (
    END_TURN,
    IllegalMove,
    action_mask,
    decode,
    legal_actions,
)
from sts.env.cards import CARD_DEFS, starter_deck
from sts.env.effects import compute_attack_damage, deal_damage
from sts.env.enemies import (
    ENCOUNTERS,
    INTENT_BASE_DAMAGE,
    roll_curl_up_block,
    roll_initial_intent,
    roll_next_intent,
    spawn_encounter,
)
from sts.env.rng import CombatRNG, shuffle_pile
from sts.env.state import CombatState, PlayerState


class Combat:
    """一场战斗的环境。用法：reset() → 循环 step(legal_actions 中的动作) 直到 done。"""

    def __init__(self, encounter: str = "jaw_worm", seed: int = 0, max_turns: int = 50):
        if encounter not in ENCOUNTERS:
            raise ValueError(f"未知遭遇：{encounter}，可选 {sorted(ENCOUNTERS)}")
        self.encounter = encounter
        self.seed = seed
        self.max_turns = max_turns  # X3 硬超时闸门（config 默认 50）
        self.state: CombatState | None = None

    # ------------------------------------------------------------- 生命周期
    def reset(self) -> None:
        """§2 战斗初始化，按编号顺序执行（消耗模式经 lightspeed 对拍验证）。"""
        rng = CombatRNG(self.seed)  # ① 4 条流同 seed 初始化
        deck = starter_deck()  # ② 固定构建顺序
        shuffle_pile(deck, rng.shuffle)  # ③ 洗牌：randomLong → 临时 java LCG → Collections.shuffle
        enemies = spawn_encounter(self.encounter, rng)  # ④ 生成敌人（louses 颜色走 misc 流）+ HP roll
        for enemy in enemies:  # ⑤ 初始意图，按生成顺序（各消耗 enemy_ai 一次）
            roll_initial_intent(enemy, rng)
        for enemy in enemies:  # ⑤' Louse Curl Up 格挡量 init 时 roll（对拍收口）
            if enemy.kind in ("louse_red", "louse_green"):
                roll_curl_up_block(enemy, rng)
        player = PlayerState()  # ⑥ HP 80 / block 0 / 能量 3 / 回合 1
        self.state = CombatState(
            player=player, enemies=enemies, draw_pile=deck, rng=rng,
        )
        self._draw(5)  # ⑦ 抽 5，槽位 0-4 按抽牌顺序
        self.state.phase = "player"  # ⑧

    @property
    def rng(self) -> CombatRNG:
        return self.state.rng

    @property
    def done(self) -> bool:
        return self.state.phase in ("won", "lost")

    @property
    def won(self) -> bool:
        return self.state.phase == "won"

    # ------------------------------------------------------------- 动作接口
    def legal_actions(self) -> list[int]:
        return legal_actions(self.state)

    def action_mask(self) -> list[bool]:
        return action_mask(self.state)

    def step(self, action: int) -> None:
        """§3 A：执行一个合法动作。非法动作一律拒绝（Gate 1 第 4 条）。"""
        if self.state.phase != "player":
            raise IllegalMove(f"战斗已结束（phase={self.state.phase}），不可行动")
        legal = self.legal_actions()
        if action not in legal:
            raise IllegalMove(f"非法动作 {action}，合法集：{legal}")
        if action == END_TURN:
            self._end_player_turn()
        else:
            self._play_card(action)

    # ------------------------------------------------------------- 玩家侧
    def _play_card(self, action: int) -> None:
        """§5 卡牌结算：扣能量 → 离开手牌 → 效果 → 入弃牌堆 → 敌灭检查。"""
        slot, target = decode(action)
        card = CARD_DEFS[self.state.hand[slot]]
        self.state.player.energy -= card.cost  # ① 先扣费
        self.state.hand.pop(slot)  # ② 离开手牌（余牌左移，槽位重排）
        enemy = self.state.enemies[target] if card.is_attack else None
        if card.is_attack:
            damage = compute_attack_damage(
                base=card.damage,
                attacker_strength=self.state.player.strength,
                attacker_weak_turns=self.state.player.weak,
                target_vulnerable_turns=enemy.vulnerable,
            )
            if deal_damage(enemy, damage) > 0:
                self._trigger_curl_up(enemy)  # Louse 首次受攻击伤害（§7，[未核实]）
            if card.vulnerable and enemy.alive:
                enemy.vulnerable += card.vulnerable  # ④ Bash：先伤害后上 Vuln
        else:
            self.state.player.block += card.block  # Defend
        self.state.discard_pile.append(card.card_id)  # ③ 置入弃牌堆
        if all(not e.alive for e in self.state.enemies):  # X1：立即胜
            self.state.phase = "won"

    def _trigger_curl_up(self, enemy) -> None:
        """Louse Curl Up：首次受到攻击伤害**启用**已 roll 好的格挡量，每场一次。

        对拍收口：格挡量在战斗初始化 roll（enemy_roll 流），受击时只启用，不再消耗。"""
        if enemy.kind not in ("louse_red", "louse_green") or enemy.curl_up_used:
            return
        enemy.curl_up_used = True
        enemy.block += enemy.curl_up_block

    # ------------------------------------------------------------- 回合切换
    def _end_player_turn(self) -> None:
        """§3 T → N → P。"""
        # T1：手牌按槽位升序（列表序）入弃牌堆
        # T1：手牌入弃牌堆——游戏从手牌高位槽位往回收（列表反序入弃，日志对拍反推：
        # 弃序影响下次洗牌排列，逐位可复现的前提）
        self.state.discard_pile.extend(reversed(self.state.hand))
        self.state.hand.clear()
        # T2：玩家 debuff 递减（受影响方回合结束时，§3 裁定）
        self.state.player.weak = max(0, self.state.player.weak - 1)
        self._enemy_turn()

    def _enemy_turn(self) -> None:
        """§3 N：按生成顺序逐个存活敌人。"""
        for enemy in self.state.enemies:
            if not enemy.alive:  # 死亡者意图作废（§4.7）
                continue
            enemy.block = 0  # N1：各自回合开始清 block
            self._execute_intent(enemy)  # N2
            if enemy.ritual:  # N3：回合结束触发（Cultist Ritual）
                # 游戏的 RitualPower 带「跳过首次」语义（lightspeed Monster.cpp:71-75
                # 注释 + 日志对拍实证：施放当回合结束不加力量）
                if enemy.ritual_skip_first:
                    enemy.ritual_skip_first = False
                else:
                    enemy.strength += 3
            # 意图在 roll 时已入史；执行时再次写入会误触发连续两次行动限制。
            roll_next_intent(enemy, self.rng)  # 下一意图：结算后立即 roll（对拍收口）
            if self.state.player.hp <= 0:  # N4 / X2：立即判负
                self.state.phase = "lost"
                return
        for enemy in self.state.enemies:  # N5：存活敌人 debuff 递减
            if enemy.alive:
                enemy.vulnerable = max(0, enemy.vulnerable - 1)
                enemy.weak = max(0, enemy.weak - 1)
        self._start_player_turn()

    def _start_player_turn(self) -> None:
        """§3 P：新玩家回合开始。"""
        p = self.state.player
        p.block = 0  # P1
        p.energy = 3  # P2
        self.state.turn += 1
        if self.state.turn > self.max_turns:  # X3：硬超时判负
            self.state.phase = "lost"
            return
        self._draw(5)  # P4

    # ------------------------------------------------------------- 抽牌
    def _draw(self, n: int) -> None:
        """§6：抽 n 张；牌库空先洗弃牌堆；双空放弃；手牌满 10 牌留牌库顶。"""
        for _ in range(n):
            if len(self.state.hand) >= 10:  # §6.4（防御性，[未核实]）
                return
            if not self.state.draw_pile:
                if not self.state.discard_pile:  # §6.3
                    return
                self.state.draw_pile = self.state.discard_pile
                self.state.discard_pile = []
                shuffle_pile(self.state.draw_pile, self.rng.shuffle)  # §6.2
            self.state.hand.append(self.state.draw_pile.pop())  # §6.1 弹出牌库顶

    # ------------------------------------------------------------- 敌人意图
    def _execute_intent(self, enemy) -> None:
        """§7 行动表执行（伤害走 §4 公式，攻击方 = 敌人、目标 = 玩家）。"""
        kind = enemy.intent
        p = self.state.player
        if kind in INTENT_BASE_DAMAGE:
            base = INTENT_BASE_DAMAGE[kind]
        elif kind == "bite":
            base = enemy.bite_damage  # 每场开局 roll 的定值（§7）
        elif kind == "bellow":
            enemy.strength += 3
            enemy.block += 6
            return
        elif kind == "incantation":
            enemy.ritual = True
            enemy.ritual_skip_first = True
            return
        elif kind == "spit_web":
            p.weak += 2
            return
        elif kind == "grow":
            enemy.strength += 3
            return
        else:
            raise ValueError(f"未知意图：{kind}")
        damage = compute_attack_damage(
            base=base,
            attacker_strength=enemy.strength,
            attacker_weak_turns=enemy.weak,
            target_vulnerable_turns=p.vulnerable,
        )
        deal_damage(p, damage)
        if kind == "thrash":  # Thrash：攻击 7 + 自身 block 5（§7）
            enemy.block += 5
