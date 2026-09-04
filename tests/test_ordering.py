"""结算顺序单测（mechanics.md §10，T01-T24）。

依据：docs/mechanics.md §10 单测清单——期望值全部从**书面规格手算推导**，
不是从实现反推（规格文档开篇声明：照文档写测试，否则测试只验证"你实现了什么"）。

约定：
- T23 规格标注"可暂 skip"。
- 构造类条目允许直接改置状态字段（手算场景，非自然对局）；被改置处均加注释说明。
- 敌人 HP 为 seed 决定的 roll 值，断言一律用「差值」（hp_before / hp_after），不锚定绝对值。
- T07 的 T1 期望按 §5.4 裁定（Bash 先伤害后上 Vuln）取 8；规格清单中"T1 伤 12"与其自身
  T2/T3 期望链（9、6）矛盾，系文档笔误，修订见 mechanics.md §11 变更记录。
"""

import random as _pyrandom

import pytest

from sts.env.actions import END_TURN, action_index
from sts.env.combat import Combat


def _play(env, card_name, target=0):
    """在手牌中找指定卡并打出（槽位 = 手牌列表下标）。"""
    slot = env.state.hand.index(card_name)
    env.step(action_index(slot, target))


def _end(env):
    env.step(END_TURN)


# ---------------------------------------------------------------- T01（P1）
def test_T01_玩家回合开始block清零():
    env = Combat(encounter="cultist", seed=1)
    env.reset()
    env.state.hand = ["defend", "strike", "strike", "strike", "strike"]
    _play(env, "defend")
    assert env.state.player.block == 5
    _end(env)  # 敌 T1：Incantation，不攻击，不碰玩家 block
    assert env.state.player.block == 0  # 新玩家回合 P1：block = 0


# ---------------------------------------------------------------- T02（N1.1）
def test_T02_敌方block先扣_下回合开始清零():
    env = Combat(encounter="jaw_worm", seed=2)
    env.reset()
    env.state.hand = ["strike"] * 5
    _end(env)  # 敌 T1：固定 Chomp
    assert env.state.player.hp == 80 - 11  # Chomp = 11
    env.state.enemies[0].intent = "thrash"  # 手工置意图（构造场景）
    _end(env)  # 敌 T2：Thrash 攻 7 + 自身 block 5
    assert env.state.player.hp == 69 - 7
    worm_hp = env.state.enemies[0].hp
    env.state.hand = ["strike"]
    env.step(action_index(0, 0))  # Strike 6：先扣 5 block，HP 仅 -1
    assert env.state.enemies[0].hp == worm_hp - 1
    env.state.enemies[0].intent = "chomp"  # T4 置无 block 技能，便于观测清零
    _end(env)  # 敌 T3：N1 先清 block，再 Chomp
    assert env.state.enemies[0].block == 0


# ---------------------------------------------------------------- T03（§4.2）
def test_T03_力量最先加入_Bellow两次后Chomp():
    env = Combat(encounter="jaw_worm", seed=3)
    env.reset()
    _end(env)  # 敌 T1：Chomp → 玩家 69
    env.state.enemies[0].strength += 6  # 等效 Bellow ×2（+3 ×2）
    env.state.enemies[0].intent = "chomp"
    _end(env)  # 敌 T2：11 + 3 + 3 = 17
    assert env.state.player.hp == 69 - 17


# ---------------------------------------------------------------- T04（§4.3）
def test_T04_易伤Strike():
    env = Combat(encounter="jaw_worm", seed=4)
    env.reset()
    env.state.hand = ["strike"]
    env.state.enemies[0].vulnerable = 2  # 直接构置
    worm_hp = env.state.enemies[0].hp
    env.step(action_index(0, 0))  # floor(6 × 1.5) = 9
    assert env.state.enemies[0].hp == worm_hp - 9


# ---------------------------------------------------------------- T05（§4.4）
def test_T05_虚弱时Strike():
    env = Combat(encounter="jaw_worm", seed=5)
    env.reset()
    env.state.hand = ["strike"]
    env.state.player.weak = 1  # 直接构置
    worm_hp = env.state.enemies[0].hp
    env.step(action_index(0, 0))  # floor(6 × 0.75) = 4
    assert env.state.enemies[0].hp == worm_hp - 4


# ---------------------------------------------------------------- T06（§4 裁定）
def test_T06_易伤先于虚弱_Bash():
    env = Combat(encounter="jaw_worm", seed=6)
    env.reset()
    env.state.hand = ["bash"]
    env.state.player.weak = 1
    env.state.enemies[0].vulnerable = 1
    worm_hp = env.state.enemies[0].hp
    # floor(floor(8×1.5)=12 ×0.75) = 9（每步乘法后立即 floor，Vuln 先于 Weak）
    env.step(action_index(0, 0))
    assert env.state.enemies[0].hp == worm_hp - 9


# ---------------------------------------------------------------- T07（N5 + §5.4）
def test_T07_Bash后两轮易伤窗口():
    env = Combat(encounter="cultist", seed=7)
    env.reset()
    env.state.hand = ["bash"]
    cult_hp = env.state.enemies[0].hp
    _play(env, "bash")  # T1：伤 8（无既有易伤，§5.4），随后 Vuln 2
    assert env.state.enemies[0].hp == cult_hp - 8
    assert env.state.enemies[0].vulnerable == 2
    _end(env)  # 敌 T1 Incantation；N5：Vuln 2→1
    env.state.hand = ["strike"]
    cult_hp = env.state.enemies[0].hp
    env.step(action_index(0, 0))  # T2：floor(6×1.5) = 9
    assert env.state.enemies[0].hp == cult_hp - 9
    _end(env)  # 敌 T2 Dark Strike；N5：Vuln 1→0
    env.state.hand = ["strike"]
    cult_hp = env.state.enemies[0].hp
    env.step(action_index(0, 0))  # T3：6
    assert env.state.enemies[0].hp == cult_hp - 6


# ---------------------------------------------------------------- T08（T2）
def test_T08_虚弱持续两个玩家回合():
    env = Combat(encounter="louses", seed=8)
    env.reset()
    red, green = env.state.enemies
    red.intent = "bite"  # 构造：红咬（不干扰断言）
    green.intent = "spit_web"  # 构造：绿吐网
    green.curl_up_used = True  # 屏蔽 Curl Up 的 block 干扰（本条只验 Weak 时序）
    green.hp = 17  # 防止 4+4+6=14 打死绿虱引入 seed 波动
    _end(env)  # 敌 T1：红 Bite、绿 Spit Web → 玩家 Weak 2
    assert env.state.player.weak == 2
    for expected in (4, 4, 6):  # 我 T2、T3 各伤 4（Weak 递减于玩家回合末），T4 伤 6
        env.state.hand = ["strike"]
        green_hp = green.hp
        env.step(action_index(0, 1))  # target 1 = 绿（第二只）
        assert green.hp == green_hp - expected
        _end(env)


# ---------------------------------------------------------------- T09（N1.3）
def test_T09_Cultist力量成长():
    env = Combat(encounter="cultist", seed=9)
    env.reset()
    _end(env)  # 敌 T1：Incantation（无攻击）
    for expected in (9, 12):  # 敌 T2：6+3=9；敌 T3：6+6=12
        player_hp = env.state.player.hp
        _end(env)
        assert env.state.player.hp == player_hp - expected


# ---------------------------------------------------------------- T10（§7）
def test_T10_敌T1无攻击():
    env = Combat(encounter="cultist", seed=10)
    env.reset()
    _end(env)  # 敌 T1：Incantation
    assert env.state.player.hp == 80  # 玩家 T1 结束时 HP 无损


# ---------------------------------------------------------------- T11（§6.2）
def test_T11_弃牌洗回再抽():
    # 规格清单原文设"T1 后 T2 抽牌触发洗牌"，但 10 张牌库起手抽 5 后 T2 抽牌时牌库
    # 尚余 5 张，洗牌最早在 T3 抽牌时触发（T1、T2 两轮各弃 5 张把手牌打光后）。
    # 本条按可达时序验同一机制：抽牌时牌库空 → 先把弃牌堆整体洗入牌库，再抽。
    env = Combat(encounter="jaw_worm", seed=11)
    env.reset()
    shuffles_before = env.rng.shuffle.count
    _end(env)  # T1：手牌 5 张入弃牌堆（牌库尚余 5，未触发洗牌）
    assert env.rng.shuffle.count == shuffles_before
    _end(env)  # T2：再弃 5 → 弃牌堆 10、牌库 0
    assert env.state.turn == 3
    assert len(env.state.hand) == 5  # 抽前牌库空 → 先洗入弃牌 10 张再抽 5
    assert env.state.discard_pile == []
    assert len(env.state.draw_pile) == 5  # 洗回 10、抽走 5
    assert env.rng.shuffle.count > shuffles_before  # 洗牌 RNG 已消耗


# ---------------------------------------------------------------- T12（§1 / §6.5）
def test_T12_同seed各流消耗逐步相同():
    a = Combat(encounter="jaw_worm", seed=12)
    a.reset()
    b = Combat(encounter="jaw_worm", seed=12)
    b.reset()
    ra = _pyrandom.Random(0)
    rb = _pyrandom.Random(0)
    for _ in range(100):
        if a.done or b.done:
            break
        assert a.rng.consumption() == b.rng.consumption()
        legal_a, legal_b = a.legal_actions(), b.legal_actions()
        assert legal_a == legal_b
        move = legal_a[ra.randrange(len(legal_a))]
        rb.randrange(len(legal_b))  # 同步消耗，保证两边脚本一致
        a.step(move)
        b.step(move)
    assert a.rng.consumption() == b.rng.consumption()


# ---------------------------------------------------------------- T13（X1）
def test_T13_击杀立即胜_敌方意图作废():
    env = Combat(encounter="cultist", seed=13)
    env.reset()
    env.state.enemies[0].hp = 5  # 构造：HP ≤ 6
    env.state.hand = ["strike"]
    env.step(action_index(0, 0))
    assert env.done and env.won
    assert env.state.player.hp == 80  # 其 Dark Strike 不再执行


# ---------------------------------------------------------------- T14（N）
def test_T14_第一只死亡第二只照常行动():
    env = Combat(encounter="louses", seed=14)
    env.reset()
    red, green = env.state.enemies
    red.hp = 5  # 构造：Strike 可击杀
    red.intent = "bite"
    green.intent = "bite"
    env.state.hand = ["strike"]
    env.step(action_index(0, 0))  # 击杀红（6 ≥ 5）
    assert red.hp <= 0
    _end(env)
    assert env.state.player.hp == 80 - green.bite_damage  # 绿照常 Bite
    assert red.hp <= 0  # 死亡者意图作废（未行动）
    assert not env.done and env.state.turn == 2


# ---------------------------------------------------------------- T15（§8.3 / §8.4）
def test_T15_非法动作与掩码():
    env = Combat(encounter="louses", seed=15)
    env.reset()
    env.state.enemies[0].hp = 0  # 构造：第一只死亡
    env.state.hand = ["strike"]
    legal = env.legal_actions()
    mask = env.action_mask()
    assert len(mask) == 31
    assert all(mask[i] == (i in legal) for i in range(31))
    assert action_index(0, 0) not in legal  # 目标死亡 → 非法
    assert action_index(0, 1) in legal  # 目标存活 → 合法
    assert END_TURN in legal
    env.state.player.energy = 0  # 构造：能量不足
    assert env.legal_actions() == [END_TURN]  # end_turn 恒合法
    with pytest.raises(Exception):
        env.step(action_index(0, 1))


# ---------------------------------------------------------------- T16（§5.4）
def test_T16_Bash不吃自上易伤():
    env = Combat(encounter="jaw_worm", seed=16)
    env.reset()
    env.state.hand = ["bash"]
    worm_hp = env.state.enemies[0].hp
    _play(env, "bash")  # 伤 8（非 12），随后 Vuln 2
    assert env.state.enemies[0].hp == worm_hp - 8
    assert env.state.enemies[0].vulnerable == 2


# ---------------------------------------------------------------- T17（§5.4）
def test_T17_Bash吃既有易伤():
    env = Combat(encounter="jaw_worm", seed=17)
    env.reset()
    env.state.hand = ["bash"]
    env.state.enemies[0].vulnerable = 1
    worm_hp = env.state.enemies[0].hp
    _play(env, "bash")  # floor(8×1.5) = 12；V1 + 2 = V3
    assert env.state.enemies[0].hp == worm_hp - 12
    assert env.state.enemies[0].vulnerable == 3


# ---------------------------------------------------------------- T18（§0）
def test_T18_同seed重置手牌一致():
    a = Combat(encounter="jaw_worm", seed=18)
    a.reset()
    b = Combat(encounter="jaw_worm", seed=18)
    b.reset()
    assert a.state.hand == b.state.hand  # ID 与槽位逐张相同
    assert a.state.draw_pile == b.state.draw_pile


# ---------------------------------------------------------------- T19（Gate 1 #3）
def test_T19_同seed随机策略200步重放一致():
    a = Combat(encounter="jaw_worm", seed=19)
    a.reset()
    b = Combat(encounter="jaw_worm", seed=19)
    b.reset()
    ra = _pyrandom.Random(7)
    rb = _pyrandom.Random(7)
    for _ in range(200):
        if a.done:
            a = Combat(encounter="jaw_worm", seed=19)
            a.reset()
            b = Combat(encounter="jaw_worm", seed=19)
            b.reset()
        assert a.state.signature() == b.state.signature()
        legal_a, legal_b = a.legal_actions(), b.legal_actions()
        assert legal_a == legal_b
        move = legal_a[ra.randrange(len(legal_a))]
        rb.randrange(len(legal_b))
        a.step(move)
        b.step(move)


# ---------------------------------------------------------------- T20（X3）
def test_T20_硬超时判负():
    env = Combat(encounter="jaw_worm", seed=20, max_turns=3)  # 缩短闸门便于手算
    env.reset()
    while not env.done:
        env.state.player.hp = 80  # 拖回合，防 X2 抢先触发
        _end(env)
    assert env.done and not env.won  # 回合数超限 → 判负


# ---------------------------------------------------------------- T21（T1）
def test_T21_弃牌堆按槽位升序():
    env = Combat(encounter="jaw_worm", seed=21)
    env.reset()
    env.state.hand = ["strike", "defend", "strike", "defend", "bash"]
    env.step(action_index(2, 0))  # 打出槽位 2 → 弃牌堆 ["strike"]
    assert env.state.discard_pile == ["strike"]
    _end(env)  # 余牌按槽位升序入弃牌堆
    assert env.state.discard_pile == ["strike", "strike", "defend", "defend", "bash"]


# ---------------------------------------------------------------- T22（§8.3）
def test_T22_能量耗尽后非法():
    env = Combat(encounter="jaw_worm", seed=22)
    env.reset()
    env.state.hand = ["bash", "strike"]  # 构造手牌
    env.step(action_index(0, 0))  # Bash 费 2 → 余 1
    assert env.state.player.energy == 1
    env.step(action_index(0, 0))  # Strike 费 1 → 余 0
    assert env.state.player.energy == 0
    assert env.legal_actions() == [END_TURN]  # 再 Strike：手牌已空，全部非法


# ---------------------------------------------------------------- T23（§6.4）
@pytest.mark.skip(reason="规格标注：防御性条目，可暂 skip")
def test_T23_手牌满抽牌失败():
    pass


# ---------------------------------------------------------------- T24（X2）
def test_T24_玩家死亡立即负_后续敌人不再行动():
    env = Combat(encounter="louses", seed=24)
    env.reset()
    red, green = env.state.enemies
    env.state.player.hp = 1  # 构造：红一咬即死
    red.intent = "bite"
    green.intent = "spit_web"
    _end(env)
    assert env.done and not env.won  # 立即判负
    assert env.state.player.weak == 0  # 绿的 Spit Web 不再执行
