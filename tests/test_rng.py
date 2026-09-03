"""rng.py 测试：Java LCG 正确性 + 流语义（mechanics.md §1 / D14）。

两个"已知向量"测试锚定逐位正确性：它们是广泛引用的 java.util.Random 首值，
一旦实现对不上即说明复刻有 bug，而不是"换了一种随机数"。
"""

import pytest

from sts.env.rng import CombatRNG, JavaRandom, RngStream


class TestJavaRandom:
    def test_known_vector_next_int_42(self):
        # new java.util.Random(42).nextInt() 的公认首值
        assert JavaRandom(42).next_int() == -1170105035

    def test_known_vector_next_double_0(self):
        # new java.util.Random(0).nextDouble() 的公认首值
        assert JavaRandom(0).next_double() == pytest.approx(0.730967787376657, rel=1e-12)

    def test_determinism_1000_draws(self):
        a, b = JavaRandom(7), JavaRandom(7)
        seq_a = [a.next_int(100) for _ in range(1000)]
        seq_b = [b.next_int(100) for _ in range(1000)]
        assert seq_a == seq_b

    def test_different_seeds_diverge_immediately(self):
        # 同种子才同序列；不同种子首值即不同（防"种子没生效"的退化情形）
        assert JavaRandom(1).next_int() != JavaRandom(2).next_int()

    def test_next_int_range_all_bounds(self):
        for bound in (1, 2, 3, 5, 10, 44, 100):
            r = JavaRandom(bound)
            draws = [r.next_int(bound) for _ in range(5000)]
            assert all(0 <= v < bound for v in draws), f"bound={bound} 越界"

    def test_next_int_power_of_two_path(self):
        r = JavaRandom(999)
        draws = [r.next_int(16) for _ in range(5000)]  # 2 的幂：走高位乘法分支
        assert all(0 <= v < 16 for v in draws)
        assert len(set(draws)) > 10  # 不是常数

    def test_next_int_no_modulo_bias(self):
        # 拒绝采样的意义：bound=3 时三个桶都应接近 1/3（模偏差会系统性偏小值）
        r = JavaRandom(3)
        draws = [r.next_int(3) for _ in range(30000)]
        for v in range(3):
            assert 9300 <= draws.count(v) <= 10700, f"桶 {v} 计数 {draws.count(v)} 偏离均匀"


class TestRngStream:
    def test_consumption_counter(self):
        s = RngStream("test", 1)
        assert s.count == 0
        s.next_int(10)
        s.next_int()
        s.next_double()
        assert s.count == 3


class TestCombatRNG:
    def test_streams_share_seed_start(self):
        # 忠实游戏结构：4 条流同 seed 初始化，同调用首值相同（§1.1 真实物理，刻意保留）
        rng = CombatRNG(42)
        assert rng.shuffle.next_int(10) == rng.enemy_ai.next_int(10)

    def test_same_seed_same_consumption_profile(self):
        # Gate 1 #3 / T12 的雏形：同 seed + 同动作脚本 → 各流取值与消耗计数完全一致
        def script(seed: int):
            rng = CombatRNG(seed)
            trace = [
                rng.shuffle.next_int(10),    # 洗牌
                rng.enemy_roll.next_int(5),  # 敌人 HP
                rng.enemy_ai.next_double(),  # AI 选择
                rng.shuffle.next_int(10),    # 再洗一次
            ]
            return trace, rng.consumption()

        t1, c1 = script(123)
        t2, c2 = script(123)
        assert t1 == t2
        assert c1 == c2 == {"shuffle": 2, "enemy_ai": 1, "enemy_roll": 1, "misc": 0}

    def test_stream_independence_under_asymmetric_load(self):
        # A 流被大量消耗后，B 流序列不受影响（对拍场景：未实现功能不消耗其他流）
        r1, r2 = CombatRNG(7), CombatRNG(7)
        for _ in range(50):
            r1.shuffle.next_int(100)
        # r1 的 enemy_roll 首值 == 全新 CombatRNG 的 enemy_roll 首值
        fresh = CombatRNG(7)
        assert r1.enemy_roll.next_int(44) == fresh.enemy_roll.next_int(44)
        assert r1.consumption() == {"shuffle": 50, "enemy_ai": 0, "enemy_roll": 1, "misc": 0}
        assert fresh.consumption() == {"shuffle": 0, "enemy_ai": 0, "enemy_roll": 1, "misc": 0}
