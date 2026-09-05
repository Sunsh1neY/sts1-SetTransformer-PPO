"""lightspeed ↔ 自写模拟器 差分对拍 harness（U6 双轨之一，spec §5.4）。

通道：slaythespire.play() 的 ConsoleSimulator 命令流（子进程 stdin 注入，零源码
改动；可行性见 lightspeed_smoke.py 冒烟）。seed 口径：seedAsLong（≥100000，
训练 seed 红线），UI 串经 pybind get_seed_str 换算后喂命令流。

当前只对拍 battle-init 的已解析字段（怪物 HP/意图、手牌/牌堆、RNG 计数）。
逐步动作对拍尚未实现，初始化一致不能证明完整战斗一致。

用法：
  python scripts/diff_harness.py            # 扫 seed + battle-init 对拍
  python scripts/diff_harness.py 100000 12  # 起始 seed 与扫描数量
"""
from __future__ import annotations

import os
import random
import re
import subprocess
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from sts.env.cards import CARD_DEFS  # noqa: E402
from sts.env.combat import Combat  # noqa: E402
from sts.env.actions import END_TURN, decode  # noqa: E402

BUILD_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "third_party", "sts_lightspeed", "build")
)

# lightspeed 怪物 id ↔ 我们的 encounter kind
MONSTER_ID_MAP = {
    "JAW_WORM": "jaw_worm",
    "CULTIST": "cultist",
    "RED_LOUSE": "louse_red",
    "GREEN_LOUSE": "louse_green",
}
# 可对拍遭遇（最小切片范围）；lightspeed 侧按怪物 id 组合识别
# 双虱颜色由 misc 流 roll 出（红+绿 / 红+红 / 绿+绿 都是合法组合）
TARGET_SETS = {
    frozenset(["jaw_worm"]): "jaw_worm",
    frozenset(["cultist"]): "cultist",
    frozenset(["louse_red", "louse_green"]): "louses",
    frozenset(["louse_red"]): "louses",
    frozenset(["louse_green"]): "louses",
}

CARD_NAME_MAP = {"Strike": "strike", "Defend": "defend", "Bash": "bash"}

# lightspeed 意图(moveHistory 首位) → 我们的意图名
INTENT_MAP = {
    "JAW_WORM_CHOMP": "chomp",
    "JAW_WORM_THRASH": "thrash",
    "JAW_WORM_BELLOW": "bellow",
    "CULTIST_INCANTATION": "incantation",
    "CULTIST_DARK_STRIKE": "dark_strike",
    "RED_LOUSE_BITE": "bite",
    "RED_LOUSE_GROW": "grow",
    "GREEN_LOUSE_BITE": "bite",
    "GREEN_LOUSE_SPIT_WEB": "spit_web",
}


def _get_ui_str(seed_long: int) -> str:
    """seedAsLong → UI 种子串（pybind 纯函数，子进程外直接调用）。"""
    if not hasattr(_get_ui_str, "_mod"):
        _get_ui_str._mod = _import_lss()
    return _get_ui_str._mod.get_seed_str(seed_long)


def _import_lss():
    import importlib

    sys.path.insert(0, BUILD_DIR)
    return importlib.import_module("slaythespire")


def run_stream(commands: str, timeout: int = 120) -> str:
    """把命令流喂给 play() 子进程，返回 stdout。"""
    p = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, r'" + BUILD_DIR + "'); "
         "import slaythespire; slaythespire.play()"],
        input=commands.encode(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
    )
    return _checked_stdout(p, "ConsoleSimulator")


def _checked_stdout(process: subprocess.CompletedProcess, label: str) -> str:
    """进程失败必须保留退出码，不能当作无战斗或解析失败跳过。"""
    if process.returncode:
        reason = process.stderr.decode(errors="replace").strip()
        if not reason and process.returncode & 0xFFFFFFFF == 0xC0000135:
            reason = "缺少运行时 DLL，请检查构建目录中的 MinGW DLL"
        reason = " ".join(reason.split())[:300] or "无 stderr 输出"
        raise RuntimeError(f"{label} 退出码 {process.returncode}: {reason}")
    return process.stdout.decode(errors="replace")


def probe_run(seed: int, col: int = 2) -> str:
    """C++ 探针通道：直接构造 run → 进首层战斗 → 返回 BattleContext 打印文本。

    比 ConsoleSimulator 子进程快两个数量级（毫秒级 vs 秒级），且不受
    Neow 界面命令流的限制；输出格式与 printActions 完全同构。"""
    probe = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "build", "lightspeed_probe.exe"))
    env = os.environ.copy()
    # 探针与扩展分处两个目录；DLL 已随本地扩展构建保存在 BUILD_DIR。
    env["PATH"] = BUILD_DIR + os.pathsep + env.get("PATH", "")
    p = subprocess.run([probe, str(seed), str(col)], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    return _checked_stdout(p, "lightspeed_probe")


# ---------------------------------------------------------------- lightspeed 侧解析
_RE_RNG = re.compile(r"aiRng: (\d+) cardRandomRng: (\d+) shuffleRng: (\d+) miscRng: (\d+) monsterHpRng: (\d+) potionRng: (\d+)")
_RE_TURN = re.compile(r"turn: (\d+), ascension (\d+), loopCount: (\d+), sum: (\d+), seed: (\d+)")
_RE_MONSTER = re.compile(
    r"\{(\d) (\w+) hp:\((\d+)/(\d+)\) block:\((\d+)\) statusEffects:\{([^}]*)\} halfDead: (\d), "
    r"moveHistory: \{ ?(\w+)?(?:, (\w+))?\}"
)
_RE_PLAYER = re.compile(r"hp:\((\d+)/(\d+)\) energy:\((\d+)/(\d+)\) block:\((\d+)\)")
_RE_PLAYER_BUFFS = re.compile(r"StatusEffects: \{([^}]*)\}")
_RE_PILE = re.compile(r"(drawPile|discardPile|exhaustPile|hand): (\d+) \{([^}]*?)\s*\}")
_RE_CARD = re.compile(r"\((\w+),")
_RE_BUFF = re.compile(r"\((\w+),(\d+)\)")


def parse_last_bc(out: str) -> dict:
    """解析最后一段 BattleContext 打印为对拍快照。"""
    i = out.rfind("BattleContext: {")
    if i == -1:
        raise ValueError("stdout 中没有 BattleContext 段；可能未进战斗或命令流断裂")
    text = out[i:]
    # CardManager 段以 hand 行 + stasisCards 行收尾；截到 stasisCards 行末
    seg = text[: text.index("stasisCards", text.index("CardManager"))] if "CardManager" in text else text

    snap: dict = {"monsters": [], "piles": {}}
    m = _RE_TURN.search(seg)
    if m:
        snap["turn"] = int(m.group(1))
        snap["seed"] = int(m.group(5))
    m = _RE_RNG.search(seg)
    if m:
        snap["rng"] = {"ai": int(m.group(1)), "card_random": int(m.group(2)),
                       "shuffle": int(m.group(3)), "misc": int(m.group(4)),
                       "monster_hp": int(m.group(5)), "potion": int(m.group(6))}
    for idx, mid, hp, hpmax, block, buffs, _hd, move_new, move_old in _RE_MONSTER.findall(seg):
        snap["monsters"].append({
            "idx": int(idx), "id": mid,
            "hp": int(hp), "hp_max": int(hpmax), "block": int(block),
            "buffs": {k: int(v) for k, v in _RE_BUFF.findall(buffs)},
            "intent": move_new,  # moveHistory 第 0 位 = 最新 roll 的意图
        })
    m = _RE_PLAYER.search(seg)
    if m:
        snap["player"] = {"hp": int(m.group(1)), "hp_max": int(m.group(2)),
                          "energy": int(m.group(3)), "block": int(m.group(5))}
        b = _RE_PLAYER_BUFFS.search(seg)
        snap["player"]["buffs"] = {k: int(v) for k, v in _RE_BUFF.findall(b.group(1))} if b else {}
    for name, count, body in _RE_PILE.findall(seg):
        snap["piles"][name] = [CARD_NAME_MAP.get(c, c.lower()) for c in _RE_CARD.findall(body)]
    return snap


def walk_to_first_battle(seed_ui: str) -> tuple[str, str]:
    """Neow 选 1（100 gold）→ map 首列 MONSTER；返回 (命令流前缀, stdout 末段位置提示)。"""
    return f"{seed_ui} IRONCLAD 0\n1\n2\n", ""


def scan_encounter(start: int = 100000, tries: int = 20) -> tuple[int, str, dict] | None:
    """从 start 起扫 seed，找首个 MONSTER 房遭遇落在最小切片范围内的 run。"""
    for offset in range(tries):
        L = start + offset
        ui = _get_ui_str(L)
        out = run_stream(f"{ui} IRONCLAD 0\n1\n2\n")
        try:
            bc = parse_last_bc(out)
        except ValueError:
            print(f"  seed {L} ({ui}): 无战斗段，跳过")
            continue
        kinds = [MONSTER_ID_MAP.get(mo["id"], mo["id"]) for mo in bc["monsters"]]
        enc = TARGET_SETS.get(frozenset(kinds))
        tag = enc or "×"
        print(f"  seed {L} ({ui}): {'+'.join(kinds)} {tag}")
        if enc:
            return L, ui, bc
    return None


# ---------------------------------------------------------------- 我们侧快照
def our_snapshot(combat: Combat, lss_intents: list[str] | None = None) -> dict:
    """我方快照。lss_intents 给出时，把 lightspeed 意图名映射为我们的意图名
    放进我们的快照（两侧意图一致 ⟺ 映射后相等；映射失败说明遭遇外意图，保留原名暴露）。"""
    s = combat.state
    intents = None
    if lss_intents is not None:
        intents = [INTENT_MAP.get(m, m) for m in lss_intents]
    return {
        "turn": s.turn - 1,  # lightspeed turn 从 0 起（玩家第一回合 turn=0）
        "monsters": [
            {
                "idx": i, "id": e.kind,
                "hp": e.hp, "hp_max": e.hp_max, "block": e.block,
                "buffs": {k: getattr(e, k) for k in ("strength", "vulnerable", "weak") if getattr(e, k)},
                "intent": intents[i] if intents is not None else e.intent,
            }
            for i, e in enumerate(s.enemies)
        ],
        "player": {
            "hp": s.player.hp, "hp_max": s.player.hp_max,
            "energy": s.player.energy, "block": s.player.block,
            "buffs": {k: getattr(s.player, k) for k in ("strength", "vulnerable", "weak") if getattr(s.player, k)},
        },
        "piles": {
            "hand": list(s.hand),
            "drawPile": list(s.draw_pile),
            "discardPile": list(s.discard_pile),
        },
        "rng": {k: v for k, v in s.rng.consumption().items()},
    }


# ---------------------------------------------------------------- 比较
def compare(ours: dict, lss: dict, ignore: tuple = ()) -> list[str]:
    diffs: list[str] = []
    if ours["turn"] != lss.get("turn"):
        diffs.append(f"turn: 我们 {ours['turn']} vs lightspeed {lss.get('turn')}")
    o, l = ours["player"], lss.get("player", {})
    for k in ("hp", "hp_max", "energy", "block"):
        if k in ignore:
            continue
        if o.get(k) != l.get(k):
            diffs.append(f"player.{k}: 我们 {o.get(k)} vs lightspeed {l.get(k)}")
    if set(o["buffs"]) - set(ignore) != {} or o["buffs"] != l.get("buffs", o["buffs"]):
        if o["buffs"] != l.get("buffs"):
            diffs.append(f"player.buffs: 我们 {o['buffs']} vs lightspeed {l.get('buffs')}")
    if len(ours["monsters"]) != len(lss.get("monsters", [])):
        diffs.append(f"怪物数: 我们 {len(ours['monsters'])} vs lightspeed {len(lss.get('monsters', []))}")
    else:
        for mo, lo in zip(ours["monsters"], lss["monsters"]):
            for k in ("id", "hp", "hp_max", "block", "intent"):
                if k in ignore:
                    continue
                if mo[k] != lo[k]:
                    diffs.append(f"monster[{mo['idx']}].{k}: 我们 {mo[k]} vs lightspeed {lo[k]}")
            if mo["buffs"] != lo["buffs"]:
                diffs.append(f"monster[{mo['idx']}].buffs: 我们 {mo['buffs']} vs lightspeed {lo['buffs']}")
    for pile in ("hand", "drawPile", "discardPile"):
        if pile in ignore:
            continue
        if ours["piles"][pile] != lss.get("piles", {}).get(pile):
            diffs.append(f"{pile}: 我们 {ours['piles'][pile]} vs lightspeed {lss.get('piles', {}).get(pile)}")
    # RNG 消耗计数（流名映射：enemy_ai↔ai，enemy_roll↔monster_hp）
    lss_rng = lss.get("rng", {})
    mapping = {"shuffle": "shuffle", "enemy_ai": "ai", "enemy_roll": "monster_hp", "misc": "misc"}
    for ours_name, lss_name in mapping.items():
        if lss_name in lss_rng and ours["rng"].get(ours_name) != lss_rng[lss_name]:
            diffs.append(f"rng.{ours_name}: 我们 {ours['rng'].get(ours_name)} vs lightspeed {lss_rng[lss_name]}")
    return diffs


# ---------------------------------------------------------------- 入口
def check_seed(seed: int, verbose: bool = True) -> str:
    """单 seed 初始化对拍；返回 pass / fail / skip，避免把故障和差异算作跳过。

    口径：combat_seed = run_seed + floorNum（BattleContext::init 公式，首层首房
    floorNum=1）；Neow 选项 1 若动了卡组或 HP，用牌堆 10 张 / HP 80 两个条件过滤。"""
    try:
        out = probe_run(seed)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"  seed {seed}: 失败，{exc}")
        return "fail"
    if "NO_BATTLE" in out[:50]:
        if verbose:
            print(f"  seed {seed}: 首房非战斗，跳过")
        return "skip"
    try:
        bc = parse_last_bc(out)
    except ValueError as exc:
        print(f"  seed {seed}: 解析失败，{exc}")
        return "fail"
    if "player" not in bc or "hand" not in bc["piles"] or not bc["monsters"]:
        print(f"  seed {seed}: 解析失败，缺少玩家、手牌或怪物字段")
        return "fail"
    n_deck = len(bc.get("piles", {}).get("hand", [])) + len(bc.get("piles", {}).get("drawPile", [])) \
        + len(bc.get("piles", {}).get("discardPile", [])) + len(bc.get("piles", {}).get("exhaustPile", []))
    if n_deck != 10 or bc["player"]["hp_max"] != 80:
        if verbose:
            print(f"  seed {seed}: Neow 奖励改变初始状态（deck={n_deck}, hp={bc['player']['hp']}/{bc['player']['hp_max']}），跳过")
        return "skip"
    kinds = [MONSTER_ID_MAP.get(m["id"], m["id"]) for m in bc["monsters"]]
    # 标准开局白名单：手牌 5（无 Snecko Eye 类抽牌改动）、格挡 0、能量 3（无 Coffee
    # Dripper 类能量遗物）、无增益状态（无 Vajra 类力量遗物）——我们环境建模的是
    # 「无祝福、仅初始遗物」的开局；不符合的种子留给第 5-6 周机制扩容后对拍
    p = bc["player"]
    if len(bc["piles"]["hand"]) != 5 or p["block"] != 0 or p["energy"] != 3 or p["buffs"]:
        if verbose:
            print(f"  seed {seed}: 非标准开局（hand={len(bc['piles']['hand'])}, block={p['block']}, "
                  f"energy={p['energy']}, buffs={p['buffs']}），跳过")
        return "skip"
    if any(m["hp"] != m["hp_max"] for m in bc["monsters"]):
        if verbose:
            print(f"  seed {seed}: Neow 1 血祝福生效（怪物非满血），跳过")
        return "skip"
    encounter = TARGET_SETS.get(frozenset(kinds))
    if encounter is None:
        if verbose:
            print(f"  seed {seed}: {'+'.join(kinds)} 不在切片范围，跳过")
        return "skip"
    combat = Combat(encounter=encounter, seed=seed + 1)
    combat.reset()
    ours = our_snapshot(combat)
    for m in bc["monsters"]:
        m["id"] = MONSTER_ID_MAP.get(m["id"], m["id"])
        m["intent"] = INTENT_MAP.get(m["intent"], m["intent"])
    diffs = compare(ours, bc)
    if diffs:
        print(f"  seed {seed} [{encounter}]: ❌ {len(diffs)} 处不一致")
        for d in diffs:
            print("    -", d)
        print("    lightspeed:", {k: bc[k] for k in ("monsters", "piles", "rng")})
        print("    我们:      ", {k: ours[k] for k in ("monsters", "piles", "rng")})
        return "fail"
    if verbose:
        print(f"  seed {seed} [{encounter}]: 初始化已比较字段一致")
    return "pass"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="仅对拍初始化的已解析字段，不含逐步战斗。")
    parser.add_argument("start", type=int, nargs="?", default=100000)
    parser.add_argument("count", type=int, nargs="?", default=12)
    args = parser.parse_args(argv)
    if args.start < 100000 or args.count <= 0:
        parser.error("起始训练 seed 须 >= 100000，扫描数量须为正数")
    lo, n = args.start, args.count
    print(f"== battle-init 批量对拍：seed {lo}..{lo + n - 1} ==")
    counts = {"pass": 0, "fail": 0, "skip": 0}
    for seed in range(lo, lo + n):
        counts[check_seed(seed)] += 1
    print(f"\n== 结果：{counts['pass']} 一致 / {counts['fail']} 失败 / {counts['skip']} 跳过 "
          "（有限初始化校准，不代表完整战斗验证）==")
    if counts["pass"] == 0:
        print("没有通过比较的样本，本次不能判定校准通过。")
    return 1 if counts["fail"] or counts["pass"] == 0 else 0


def _dump(snap: dict) -> None:
    import json

    print(json.dumps(snap, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
