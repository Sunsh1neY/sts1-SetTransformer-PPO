"""rng.py 测试：xorshift128+ 正确性 + 流语义（mechanics.md §1 / D14 修订）。

真值锚定分两层：
- C++ 真值：本机对 lightspeed ``sts::Random`` 直编程序（reference/rng_truth.cpp）
  打印的序列，逐位对照——这是"复刻对没对"的权威依据（D13 使用阶梯）；
- JavaRandom（洗牌临时实例）：保留 java.util.Random 公认首值向量。
"""

import pytest

from sts.env.rng import CombatRNG, JavaRandom, RngStream, StsRandom, shuffle_pile


def _s64(x: int) -> int:
    return x - (1 << 64) if x >= (1 << 63) else x


class TestStsRandom:
    def test_truth_random_long_seed142(self):
        # reference/rng_truth.exe（lightspeed 源直编）seed=142 randomLong x4
        r = StsRandom(142)
        got = [_s64(r.random_long()) for _ in range(4)]
        assert got == [
            -1118907959237577578,
            -2279754084557898738,
            6896908717761790281,
            7055937689730694401,
        ]

    def test_truth_random_int_seed142(self):
        # rng_truth: random(99) x4 → 19 39 40 0
        r = StsRandom(142)
        assert [r.random_int(99) for _ in range(4)] == [19, 39, 40, 0]

    def test_truth_mixed_seed142(self):
        # rng_truth: random(10,15)=11, random(11,17)=16, random(5,7)=6,
        #            randomBoolean=1, randomBoolean(0.75)=1
        r = StsRandom(142)
        assert r.random_int_range(10, 15) == 11
        assert r.random_int_range(11, 17) == 16
        assert r.random_int_range(5, 7) == 6
        assert r.random_boolean() is True
        assert r.random_boolean(0.75) is True

    def test_truth_seed100002(self):
        # rng_truth: seed=100002 randomLong x2
        r = StsRandom(100002)
        assert [_s64(r.random_long()) for _ in range(2)] == [
            -5454665337330764102,
            835346377173556035,
        ]

    def test_counter_semantics(self):
        # counter 只在 random* 系列递增（游戏存档语义，对拍依赖）
        r = StsRandom(5)
        assert r.counter == 0
        r._next_long()  # 裸 next* 不递增
        assert r.counter == 0
        r.random_long()
        r.random_int(10)
        r.random_boolean()
        assert r.counter == 3

    def test_determinism_1000_draws(self):
        a, b = StsRandom(7), StsRandom(7)
        assert [a.random_int(100) for _ in range(1000)] == [b.random_int(100) for _ in range(1000)]

    def test_int_range_bounds_and_coverage(self):
        for lo, hi in ((10, 15), (3, 7), (40, 44), (5, 5)):
            r = StsRandom(lo * hi + 1)
            draws = [r.random_int_range(lo, hi) for _ in range(3000)]
            assert all(lo <= v <= hi for v in draws), f"[{lo},{hi}] 越界"
            if hi > lo:
                assert set(draws) == set(range(lo, hi + 1)), f"[{lo},{hi}] 未全覆盖"


class TestJavaRandom:
    def test_known_vector_next_int_42(self):
        # new java.util.Random(42).nextInt() 的公认首值
        assert JavaRandom(42).next(32) == -1170105035

    def test_known_vector_first_next_int_bound(self):
        # new java.util.Random(42).nextInt(10) 公认首值 0（社区广泛引用向量）
        assert JavaRandom(42).next_int(10) == 0

    def test_rejection_sampling_no_modulo_bias(self):
        r = JavaRandom(3)
        draws = [r.next_int(3) for _ in range(30000)]
        for v in range(3):
            assert 9300 <= draws.count(v) <= 10700, f"桶 {v} 计数 {draws.count(v)} 偏离均匀"


class TestRngStream:
    def test_counter_via_property(self):
        s = RngStream("shuffle", 42)
        assert s.count == 0
        s.random_int(10)
        s.random_long()
        assert s.count == 2

    def test_same_seed_same_stream_values(self):
        a, b = RngStream("x", 42), RngStream("x", 42)
        assert [a.random_int(99) for _ in range(10)] == [b.random_int(99) for _ in range(10)]


class TestCombatRNG:
    def test_four_streams_same_start(self):
        """四流同 seed 同状态起步：首值相同是游戏真实物理（D14 修订）。"""
        rng = CombatRNG(42)
        vals = [rng.shuffle.random_int(99), rng.enemy_ai.random_int(99),
                rng.enemy_roll.random_int(99), rng.misc.random_int(99)]
        assert len(set(vals)) == 1

    def test_stream_independence_under_asymmetric_load(self):
        # A 流被大量消耗后，B 流序列不受影响（对拍场景：未实现功能不消耗其他流）
        r1, r2 = CombatRNG(7), CombatRNG(7)
        for _ in range(50):
            r1.shuffle.random_int(100)
        assert [r1.enemy_ai.random_int(99) for _ in range(10)] == [r2.enemy_ai.random_int(99) for _ in range(10)]

    def test_consumption_profile(self):
        rng = CombatRNG(9)
        rng.shuffle.random_long()      # 洗牌
        rng.enemy_roll.random_int_range(10, 15)  # 敌人 HP
        rng.enemy_ai.random_int(99)    # 意图
        assert rng.consumption() == {"shuffle": 1, "enemy_ai": 1, "enemy_roll": 1, "misc": 0}


class TestShufflePile:
    def test_truth_shuffle_seed143(self):
        """战斗开局洗牌真值：CombatRNG(143)（=run 142 + floor 1）的洗牌排列。

        权威数据：bc_truth.exe 打印 drawPile uniqueIds [2,6,3,7,4,1,0,8,9,5]，
        Python 侧 Python 循环逐位复现（2026-09-04 对拍收口）。
        """
        rng = CombatRNG(143)
        pile = list(range(10))
        shuffle_pile(pile, rng.shuffle)
        assert pile == [2, 6, 3, 7, 4, 1, 0, 8, 9, 5]
        assert rng.shuffle.count == 1  # 每次洗牌恰好消耗 1 次 randomLong

    def test_empty_and_single(self):
        """C++ 侧 randomLong() 作参数总先求值：0/1 张也消耗 1 次（忠实复刻）。"""
        rng = CombatRNG(1)
        for pile in ([], ["bash"]):
            shuffle_pile(pile, rng.shuffle)
            assert rng.shuffle.count == 1
            rng.shuffle._rng.counter = 0  # 复位以便下一轮断言
