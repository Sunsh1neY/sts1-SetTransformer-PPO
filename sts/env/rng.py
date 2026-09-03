"""独立 RNG 流 —— java.util.Random 的逐位复刻（D14，2026-09-03）。

为什么复刻 Java 而不是用 numpy（docs/decisions.md D14）：

- 游戏本体的战斗随机性来自 5 个独立的 ``java.util.Random`` 实例（mechanics.md §1.1，
  反编译 ``generateSeeds()`` 已核实）——48-bit 线性同余生成器（LCG）；
- 第 3 周日志回放对拍要求「同 run seed + 同动作序列 → 同状态」，随机序列必须与游戏
  **逐位一致**；
- U6 若纳入 lightspeed 差分，同样要求 seed 对齐（其自称 100% RNG accurate，即 Java LCG）。

numpy 的 PCG64 与 Java LCG 是完全不同的算法，同 seed 的序列毫无关系，故环境内不使用
numpy。训练/评估统计侧的随机性（第 7 周起）由 torch 生成器负责，与本模块无关。

流间相关性是游戏真实物理，**刻意保留**：游戏每层用同一个 run seed 重建全部战斗流，
流间独立性只来自"独立实例 + 各自的消耗序列"（ ForgottenArbiter《Correlated
Randomness》分析过这种相关性）。我们不"改良"它——忠实复刻是对拍成立的前提。

消耗计数器是可复现性断言的一部分（Gate 1 第 3 条、mechanics.md T12）：
同一 seed + 同一动作序列，各流的消耗次数与取值必须逐步相同。
"""

_MULTIPLIER = 0x5DEECE66D  # java.util.Random 的乘数与加数，javadoc 公开常量
_ADDEND = 0xB
_MASK48 = (1 << 48) - 1
_INT32 = 1 << 32


def _to_signed32(x: int) -> int:
    x &= _INT32 - 1
    return x - _INT32 if x >= 1 << 31 else x


class JavaRandom:
    """``java.util.Random``（JDK 8 语义）的精确复刻。算法全部来自其 javadoc：

    - ``next(bits)``：``seed = (seed * 0x5DEECE66D + 0xB) mod 2^48``，取高 bits 位（有符号）；
    - ``nextInt(bound)``：2 的幂走高位乘法，否则拒绝采样消除模偏差；
    - ``nextDouble()``：26 + 27 共 53 位随机尾数。
    """

    def __init__(self, seed: int) -> None:
        self._seed = (seed ^ _MULTIPLIER) & _MASK48

    def next(self, bits: int) -> int:
        if not 1 <= bits <= 32:
            raise ValueError("bits 必须在 [1, 32]")
        self._seed = (self._seed * _MULTIPLIER + _ADDEND) & _MASK48
        return _to_signed32(self._seed >> (48 - bits))

    def next_int(self, bound: int | None = None) -> int:
        if bound is None:
            return self.next(32)
        if bound <= 0:
            raise ValueError("bound 必须为正")
        if bound & (bound - 1) == 0:  # 2 的幂：取 31 位的高位，避免低位偏差
            return (bound * self.next(31)) >> 31
        while True:  # 拒绝采样：bits - val + (bound-1) 在 Java 中溢出为负时重试
            bits = self.next(31)
            val = bits % bound
            if bits - val + (bound - 1) < 1 << 31:
                return val

    def next_double(self) -> float:
        return ((self.next(26) << 27) + self.next(27)) * 2.0**-53


class RngStream:
    """一条命名流：JavaRandom 实例 + 消耗计数。

    计数纳入可复现性断言：同 seed 同动作序列下，每条流的消耗次数必须逐步相同。
    """

    def __init__(self, name: str, seed: int) -> None:
        self.name = name
        self._rng = JavaRandom(seed)
        self.count = 0

    def next_int(self, bound: int | None = None) -> int:
        self.count += 1
        return self._rng.next_int(bound)

    def next_double(self) -> float:
        self.count += 1
        return self._rng.next_double()


class CombatRNG:
    """一场战斗的 4 条专用流（mechanics.md §1）。

    与游戏一致（§1.1）：**全部用同一个 combat seed 初始化**，不做不同种子派生——
    游戏本体每层以 run seed 重建全部战斗流，独立实例 + 各自消耗即独立性来源。
    洗牌流与敌人 roll 流的首值相同是游戏的真实物理，不是 bug。
    """

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.shuffle = RngStream("shuffle", seed)      # 洗牌、抽牌顺序（游戏: shuffleRng）
        self.enemy_ai = RngStream("enemy_ai", seed)    # 敌人行动选择（游戏: aiRng）
        self.enemy_roll = RngStream("enemy_roll", seed)  # 敌人 HP 等 roll（游戏: monsterHpRng）
        self.misc = RngStream("misc", seed)            # 预留（游戏: miscRng）

    def consumption(self) -> dict[str, int]:
        return {
            s.name: s.count
            for s in (self.shuffle, self.enemy_ai, self.enemy_roll, self.misc)
        }
