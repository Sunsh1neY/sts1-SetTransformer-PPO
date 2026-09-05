"""独立 RNG 流 —— 游戏本体双层 RNG 的逐位复刻（D14 修订，2026-09-04 对拍收口）。

**规格来源**（D13 使用阶梯：lightspeed 源码仲裁；runlogger 日志对拍为最终真值）：

- **通道层**：``sts::Random`` = murmurHash3 初始化的 xorshift128+（lightspeed
  ``include/game/Random.h``）。``counter`` 随每次 ``random*`` 系列调用递增，是可
  复现性断言的一部分（游戏存档即如此）。
- **洗牌层**：每次洗牌消耗 ``shuffleRng.randomLong()`` 一个 long，以其为种子构造
  **临时** ``java.util.Random``（48 位 LCG），再执行 Java 标准库
  ``Collections.shuffle``（lightspeed ``src/combat/Actions.cpp:183-198``）。
- **战斗内派生**（``BattleContext::init``）：aiRng / monsterHpRng / shuffleRng /
  cardRandomRng 四条流由 ``Random(runSeed + floorNum)`` **同一状态拷贝**初始化；
  miscRng / potionRng 从 run 级继承。
- 第 2 周「战斗随机性 = java.util.Random 逐位复刻」的假设被第 3 周差分对拍推翻
  （16 处差异定位到 RNG 核心），已在 docs/decisions.md D14 修订条目登记。
  ``JavaRandom`` 保留但降级为洗牌临时实例。

流间相关性是游戏真实物理，**刻意保留**：四流同 seed 同状态起步，独立性只来自
「独立实例 + 各自的消耗序列」。我们不"改良"它——忠实复刻是对拍成立的前提。

消耗计数器纳入可复现性断言（Gate 1 第 3 条、mechanics.md T12）：同一 seed +
同一动作序列，各流消耗次数与取值必须逐步相同。
"""

import struct

_M64 = (1 << 64) - 1
_MURMUR_C1 = 0xFF51AFD7ED558CCD  # murmurHash3 finalizer 常量（Random.h）
_MURMUR_C2 = 0xC4CEB9FE1A85EC53
_ONE_IN_MOST_SIGNIFICANT = 1 << 63  # seed==0 时的替代种子（Random.h）

_NORM_DOUBLE = 2.0**-53  # 1.1102230246251565E-16
_NORM_FLOAT = 2.0**-24  # 5.9604644775390625E-8

# java.util.Random（洗牌临时实例用）
_MULTIPLIER = 0x5DEECE66D
_ADDEND = 0xB
_MASK48 = (1 << 48) - 1
_INT32 = 1 << 32


def _to_signed32(x: int) -> int:
    x &= _INT32 - 1
    return x - _INT32 if x >= 1 << 31 else x


def _to_float32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


def murmur_hash3(x: int) -> int:
    """64 位 murmurHash3 finalizer（Random.h::murmurHash3），全程无符号 64 位。"""
    x &= _M64
    x ^= x >> 33
    x = (x * _MURMUR_C1) & _M64
    x ^= x >> 33
    x = (x * _MURMUR_C2) & _M64
    x ^= x >> 33
    return x


class StsRandom:
    """``sts::Random``（xorshift128+）的逐位复刻，游戏全部随机通道的底层。

    C++ 无符号溢出语义用 ``& _M64`` 对齐；``counter`` 语义与游戏一致——仅
    ``random*`` 系列递增（裸 ``next*`` 系列不递增），与 lightspeed 完全相同。
    """

    def __init__(self, seed: int) -> None:
        self.counter = 0
        seed &= _M64
        self._seed0 = murmur_hash3(seed if seed != 0 else _ONE_IN_MOST_SIGNIFICANT)
        self._seed1 = murmur_hash3(self._seed0)

    def _next_long(self) -> int:
        """xorshift128+ 主生成（无符号 64 位）。"""
        s1 = self._seed0
        s0 = self._seed1
        self._seed0 = s0
        s1 ^= (s1 << 23) & _M64
        self._seed1 = (s1 ^ s0 ^ (s1 >> 17) ^ (s0 >> 26)) & _M64
        return (self._seed1 + s0) & _M64

    def _next_long_bound(self, n: int) -> int:
        """``nextLong(n)``：63 位无符号取模 + int64 溢出拒绝采样（Random.h）。"""
        while True:
            bits = self._next_long() >> 1
            value = bits % n
            diff = bits - value + (n - 1)
            signed = diff - (1 << 64) if diff >= 1 << 63 else diff
            if signed >= 0:
                return value

    def next_double(self) -> float:
        return (self._next_long() >> 11) * _NORM_DOUBLE

    def next_float(self) -> float:
        # C++ 先做 double 乘法再截断为 float，边界值必须对齐
        return _to_float32((self._next_long() >> 40) * _NORM_FLOAT)

    # ------------------------------------------------- random* 系列（counter++）
    def random_long(self) -> int:
        self.counter += 1
        return self._next_long()

    def random_int(self, range_: int) -> int:
        """``random(int32 range)``：[0, range] 含两端整数（GDX 语义）。"""
        self.counter += 1
        return self._next_long_bound(range_ + 1)

    def random_int_range(self, start: int, end: int) -> int:
        """``random(int32 start, int32 end)``：整数均匀，含两端。"""
        self.counter += 1
        return start + self._next_long_bound(end - start + 1)

    def random_double_range(self, start: int, end: int) -> int:
        """``random(int64 start, int64 end)``：nextDouble 乘区间后截断（浮点路径）。"""
        self.counter += 1
        return start + int(self.next_double() * (end - start))

    def random_boolean(self, chance: float | None = None) -> bool:
        self.counter += 1
        if chance is None:
            return bool(self._next_long() & 1)
        return self.next_float() < chance


class JavaRandom:
    """``java.util.Random``（JDK 8 语义）的精确复刻——**仅作洗牌临时实例**。

    对拍证据：战斗洗牌每次以 ``shuffleRng.randomLong()`` 为种子新建 LCG 实例执行
    ``Collections.shuffle``，随后即弃（Actions.cpp:183-186）。seed 允许 64 位
    无符号（C++ 侧 ``java::Random(std::uint64_t)``）。
    """

    def __init__(self, seed: int) -> None:
        self._seed = ((seed & _M64) ^ _MULTIPLIER) & _MASK48

    def next(self, bits: int) -> int:
        if not 1 <= bits <= 32:
            raise ValueError("bits 必须在 [1, 32]")
        self._seed = (self._seed * _MULTIPLIER + _ADDEND) & _MASK48
        return _to_signed32(self._seed >> (48 - bits))

    def next_int(self, bound: int) -> int:
        if bound <= 0:
            raise ValueError("bound 必须为正")
        if bound & (bound - 1) == 0:  # 2 的幂：取 31 位的高位，避免低位偏差
            return (bound * self.next(31)) >> 31
        while True:  # 拒绝采样：bits - val + (bound-1) 在 Java 中溢出为负时重试
            bits = self.next(31)
            val = bits % bound
            if bits - val + (bound - 1) < 1 << 31:
                return val


class RngStream:
    """一条命名流：StsRandom 实例 + 游戏语义的随机方法。

    消耗计数直接读 ``rng.counter``（与游戏 counter 语义一致），不再单独维护。
    """

    def __init__(self, name: str, seed: int) -> None:
        self.name = name
        self._rng = StsRandom(seed)

    @property
    def count(self) -> int:
        return self._rng.counter

    def random_long(self) -> int:
        return self._rng.random_long()

    def random_int(self, range_: int) -> int:
        return self._rng.random_int(range_)

    def random_int_range(self, start: int, end: int) -> int:
        return self._rng.random_int_range(start, end)

    def random_boolean(self, chance: float | None = None) -> bool:
        return self._rng.random_boolean(chance)


def shuffle_pile(pile: list, shuffle_stream: RngStream) -> None:
    """游戏双层洗牌（Actions.cpp:183-186）：randomLong → 临时 java LCG → shuffle。

    ``Collections.shuffle`` 语义：i 从 size 到 2，``swap(pile[i-1], pile[nextInt(i)])``。
    每次调用恰好消耗 shuffle 流 1 次（randomLong），与对拍观察一致。
    """
    jr = JavaRandom(shuffle_stream.random_long())
    for i in range(len(pile), 1, -1):
        j = jr.next_int(i)
        pile[i - 1], pile[j] = pile[j], pile[i - 1]


class CombatRNG:
    """一场战斗的 4 条专用流（mechanics.md §1）。

    ``combat_seed = run_seed + floor_num``（BattleContext::init 公式）；四流由同一
    状态拷贝初始化（等价于同 seed 各建实例）。misc 流在游戏里从 run 级继承计数，
    环境当前无 run 层，战斗从 0 起算——对拍时的偏差只允许出现在 misc 流前置计数。
    """

    def __init__(self, combat_seed: int) -> None:
        self.seed = combat_seed
        self.shuffle = RngStream("shuffle", combat_seed)  # 游戏洗牌流（洗牌 + 抽牌顺序）
        self.enemy_ai = RngStream("enemy_ai", combat_seed)  # 敌人意图 roll（游戏: aiRng）
        self.enemy_roll = RngStream("enemy_roll", combat_seed)  # 敌人 HP/咬伤/Curl Up（游戏: monsterHpRng）
        self.misc = RngStream("misc", combat_seed)  # 杂项 roll（游戏: miscRng，run 级继承）

    def consumption(self) -> dict[str, int]:
        return {
            s.name: s.count
            for s in (self.shuffle, self.enemy_ai, self.enemy_roll, self.misc)
        }
