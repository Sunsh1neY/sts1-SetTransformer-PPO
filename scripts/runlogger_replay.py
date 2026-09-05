"""runlogger 日志回放对拍器（现有日志的有限校准）。

日志 schema（2026-09-04 实测，colinking/runlogger 0.1.0 + Determinism Fix 1.0.0）：
- **GBK 编码**的 JSONL（游戏本地化文本随日志落盘）；每行一个 JSON 对象带 ``_type``。
- ``state:run``：seed（UI 串）+ 职业 + 进阶 + mods 清单，恒为首行；
- ``state:floor``：动作后的已记录字段快照——战斗层含 ``combat_state``（hand /
  draw_pile / discard_pile / monsters / player）与 ``seeds``（各随机通道消耗计数，
  与 lightspeed bc 打印的 counter 同源同义）；
- 动作：``select_dialog{index}`` / ``select_map{x}`` / ``play_card{card_index,
  target_index?}`` / ``end_turn`` / ``select_reward{reward,reward_index}`` /
  ``select_card{reward_index,card_index}`` / ``abandon``。

本脚本实现**日志 → lightspeed 重放**（通道校准）：把日志动作序列翻译成
ConsoleSimulator 命令流重放，逐步与日志快照比较已记录字段。
结果不能单独证明完整状态或终局结算一致。
对任意遭遇可用（包括尚未实现进自写模拟器的）。

界面差异对齐规则（真游戏 UI 比命令模型多步骤）：
- 连续多条 select_dialog 只取第一条（后续是确认弹窗，lightspeed 无此屏）；
- 奖励屏动作后若回到地图，先补一条 ``proceed``（真游戏自动前进，命令模型要显式发）。

只验证已记录字段；缺失的格挡、状态效果和终局快照保留为未验证。
用法：python scripts/runlogger_replay.py [日志路径]（缺省读取 runlogs 目录全部日志）
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from diff_harness import BUILD_DIR, parse_last_bc, run_stream  # noqa: E402

GAME_DIR = r"E:\SteamLibrary\steamapps\common\SlayTheSpire"
RUNLOGS_DIR = os.path.join(GAME_DIR, "runlogs")

# 日志卡名（本地化）→ 模拟器卡 id；未收录的卡在报告中标注（第 5-6 周扩容补表）
CARD_NAME_MAP = {
    "打击": "strike",
    "防御": "defend",
    "痛击": "bash",
    "黏液": "slimed",
}

def map_pile(pile: list[str]) -> list[str | None]:
    """日志本地化卡名 → 模拟器卡 id；未收录的返回 None（报告人工核对）。"""
    return [CARD_NAME_MAP.get(c) for c in pile]


# 招式名 → 日志意图类别（runlogger 枚举实测：ATTACK / ATTACK_DEBUFF / ATTACK_DEFEND /
# DEFEND_BUFF / DEBUFF / BUFF ...）；未收录项不判分，报告人工核对
INTENT_CATEGORY = {
    "ACID_SLIME_S_TACKLE": "ATTACK", "ACID_SLIME_S_LICK": "DEBUFF",
    "ACID_SLIME_S_CORROSIVE_SPIT": "ATTACK_DEBUFF",
    "SPIKE_SLIME_M_TACKLE": "ATTACK", "SPIKE_SLIME_M_LICK": "DEBUFF",
    "SPIKE_SLIME_M_CUT": "ATTACK_DEBUFF", "SPIKE_SLIME_M_FLAME_TACKLE": "ATTACK_DEBUFF",
    "JAW_WORM_CHOMP": "ATTACK", "JAW_WORM_THRASH": "ATTACK_DEFEND",
    "JAW_WORM_BELLOW": "DEFEND_BUFF",
    "CULTIST_INCANTATION": "BUFF", "CULTIST_DARK_STRIKE": "ATTACK",
    "RED_LOUSE_BITE": "ATTACK", "RED_LOUSE_GROW": "BUFF",
    "GREEN_LOUSE_BITE": "ATTACK", "GREEN_LOUSE_SPIT_WEB": "DEBUFF",
}


def parse_runlog(path: str) -> dict:
    """解析 .run.log；所有对象带 ``_order``（文件行序），用于动作-快照对齐。"""
    raw = open(path, "rb").read().decode("gbk", errors="replace")
    objs = [json.loads(line) for line in raw.splitlines() if line.strip()]
    for i, o in enumerate(objs):
        o["_order"] = i
    run = objs[0]
    assert run["_type"] == "state:run", "日志首行必须是 state:run"
    return {
        "seed_ui": run["seed"], "class": run["class"], "ascension": run["ascension"],
        "mods": run.get("mods", {}),
        "events": [o for o in objs[1:] if o["_type"].startswith("action:")],
        "floors": [o for o in objs[1:] if o["_type"] == "state:floor"],
    }


def build_commands(run: dict) -> list[tuple[dict, str]]:
    """日志动作序列 → [(动作, 命令)]，应用界面差异对齐规则。

    对齐规则（真游戏 UI 与命令模型的差异）：
    - dialog 动作只在其所处屏幕的**选项数 > 1** 时发命令（真正的选择屏）；
      单选项屏（Neow 的「对话」/「离开」过渡屏）跳过——lightspeed 没有这些层；
    - 奖励屏动作后若回到地图，先补一条 ``proceed``（真游戏自动前进，命令模型要显式发）。
    """
    timeline = sorted(run["events"] + run["floors"], key=lambda o: o["_order"])
    last_options = 0
    out: list[tuple[dict, str]] = []
    last_kind = "seed"
    for obj in timeline:
        if obj["_type"] == "state:floor":
            opts = obj.get("screen_state", {}).get("options")
            last_options = len(opts) if opts else 0
            continue
        t = obj["_type"]
        if t == "action:abandon":
            break
        if t == "action:select_dialog":
            if last_options <= 1:
                continue  # 过渡屏（进入/离开），lightspeed 无此层
            out.append((obj, str(obj["index"])))
            last_kind = "select_dialog"
        elif t == "action:select_map":
            if last_kind in ("select_reward", "select_card"):
                out.append(({"_type": "synthetic:proceed", "_order": obj["_order"]}, "proceed"))
            out.append((obj, str(obj["x"])))
            last_kind = "select_map"
        elif t == "action:play_card":
            cmd = str(obj["card_index"])
            if "target_index" in obj:
                cmd += f" {obj['target_index']}"
            out.append((obj, cmd))
            last_kind = "play_card"
        elif t == "action:end_turn":
            out.append((obj, "end"))
            last_kind = "end_turn"
        elif t == "action:select_reward":
            out.append((obj, f"{obj['reward'].lower()} {obj['reward_index']}"))
            last_kind = "select_reward"
        elif t == "action:select_card":
            out.append((obj, f"card {obj['reward_index']} {obj['card_index']}"))
            last_kind = "select_card"
        else:
            out.append((obj, None))  # 未支持动作：跳过并报告
    return out


def norm_id(name: str) -> str:
    """怪物 id 归一化：日志 CamelCase（AcidSlime_S）与 lightspeed（ACID_SLIME_S）统一。"""
    return re.sub(r"[^A-Z0-9]", "", name.upper())


def _compare_status(model: dict, logged: dict, prefix: str, diffs: list[str],
                    unverified: set[str], label: str) -> None:
    """缺失状态不能当作 0；只比较双方实际记录的字段。"""
    for key in ("block", "buffs"):
        if key not in logged or key not in model:
            unverified.add(f"{prefix}.{key}")
        elif logged[key] != model[key]:
            diffs.append(f"{prefix}.{key}: 日志 {logged[key]} vs {label} {model[key]}")


def _compare_player(model: dict, snap: dict, diffs: list[str],
                    unverified: set[str], label: str) -> None:
    logged = snap.get("combat_state", {}).get("player", {})
    for log_key, model_key in (("hp_current", "hp"), ("hp_max", "hp_max")):
        source = snap if log_key in snap else logged
        if log_key not in source or model_key not in model:
            unverified.add(f"player.{model_key}")
        elif source[log_key] != model[model_key]:
            diffs.append(f"player.{model_key}: 日志 {source[log_key]} vs {label} {model[model_key]}")
    if "energy" not in logged or "energy" not in model:
        unverified.add("player.energy")
    elif logged["energy"] != model["energy"]:
        diffs.append(f"player.energy: 日志 {logged['energy']} vs {label} {model['energy']}")
    _compare_status(model, logged, "player", diffs, unverified, label)


def compare_snapshot(bc: dict, snap: dict, unverified: set[str] | None = None) -> list[str]:
    """返回已比较字段的差异；空列表只表示这些字段一致，不表示全量状态通过。"""
    diffs: list[str] = []
    if unverified is None:
        unverified = set()
    lc = snap.get("combat_state", {})
    lss_mons = sorted(bc["monsters"], key=lambda monster: monster.get("idx", 0))
    log_mons = lc.get("monsters", [])
    if len(lss_mons) != len(log_mons):
        diffs.append(f"怪物数: lightspeed {len(lss_mons)} vs 日志 {len(log_mons)}")
    # 按实体位置比对，不能用类型名作字典键，否则同类怪物会互相覆盖。
    for i, (lm, bm) in enumerate(zip(log_mons, lss_mons)):
        mid = f"monster[{i}]"
        if norm_id(lm["id"]) != norm_id(bm["id"]):
            diffs.append(f"{mid}.id: 日志 {lm['id']} vs lightspeed {bm['id']}")
        if (lm["hp_current"], lm["hp_max"]) != (bm["hp"], bm["hp_max"]):
            diffs.append(f"{mid}.hp: 日志 {lm['hp_current']}/{lm['hp_max']} vs lightspeed {bm['hp']}/{bm['hp_max']}")
        if lm.get("is_gone") and bm["hp"] > 0:
            diffs.append(f"{mid}: 日志已死但 lightspeed 存活")
        log_intent = lm.get("intent")
        if log_intent and bm["intent"]:
            mapped = INTENT_CATEGORY.get(bm["intent"])
            if mapped is None:
                unverified.add(f"{mid}.intent（未收录映射 {bm['intent']}）")
            elif mapped != log_intent:
                diffs.append(f"{mid}.intent: 日志 {log_intent} vs lightspeed {bm['intent']}({mapped})")
        else:
            unverified.add(f"{mid}.intent")
        _compare_status(bm, lm, mid, diffs, unverified, "lightspeed")
    _compare_player(bc.get("player", {}), snap, diffs, unverified, "lightspeed")
    for log_key, ls_key in (("hand", "hand"), ("draw_pile", "drawPile"), ("discard_pile", "discardPile")):
        if log_key not in lc:
            unverified.add(ls_key)
            continue
        mapped = [CARD_NAME_MAP.get(c) for c in lc[log_key]]
        if any(c is None for c in mapped):
            unverified.add(f"{ls_key}（含未收录卡名）")
            continue
        if mapped != bc["piles"].get(ls_key):
            diffs.append(f"{ls_key}: 日志 {mapped} vs lightspeed {bc['piles'].get(ls_key)}")
    log_seeds = snap.get("seeds", {})
    for k_ours, k_log in (("ai", "ai"), ("shuffle", "shuffle"), ("misc", "misc"),
                          ("monster_hp", "monster_hp"), ("card_random", "card_random"), ("potion", "potion")):
        if k_log in log_seeds and k_ours in bc.get("rng", {}):
            if log_seeds[k_log] != bc["rng"][k_ours]:
                diffs.append(f"rng.{k_ours}: 日志 {log_seeds[k_log]} vs lightspeed {bc['rng'][k_ours]}")
        else:
            unverified.add(f"rng.{k_ours}")
    return diffs


def snapshot_after(run: dict, order: int) -> dict | None:
    """文件序号 order 的动作之后，第一条含 combat_state 的 state:floor；
    若先遇到离开战斗房（room_type 变化且无 combat_state）则返回 None。"""
    for f in run["floors"]:
        if f["_order"] <= order:
            continue
        if "combat_state" in f:
            return f
        return None  # 进入下一个非战斗屏：该动作是战斗收尾
    return None


def replay_log(run: dict, verbose: bool = True) -> dict:
    """重放整份日志到 lightspeed 并逐步对拍战斗步骤。返回统计。"""
    pairs = build_commands(run)
    cmds = [f"{run['seed_ui']} {run['class']} {run['ascension']}"]
    cmds += [c for _, c in pairs if c is not None]
    cmds.append("quit")
    out = run_stream("\n".join(cmds) + "\n")

    # stdout 按 '<< ' 回显切段：种子行无回显前缀，段[i] 对应 cmds[i+1] = pairs[i]
    segs = re.split(r"^<< ", out, flags=re.MULTILINE)[1:]

    stats = {"steps": 0, "pass": 0, "diff": 0, "skip": 0, "issues": [], "unverified": []}
    unverified: set[str] = set()
    segment_index = 0
    for i, (ev, cmd) in enumerate(pairs):
        if cmd is None:
            stats["skip"] += 1
            stats["issues"].append(f"step{i}: 未支持的动作 {ev['_type']}，跳过")
            continue
        seg = segs[segment_index] if segment_index < len(segs) else ""
        segment_index += 1
        if ev["_type"] not in ("action:play_card", "action:end_turn"):
            continue  # 战斗外动作：只重放（校准通道），无逐步对拍
        snap = snapshot_after(run, ev["_order"])
        if snap is None:
            stats["skip"] += 1  # 战斗收尾动作（击杀后），无战斗态快照
            stats["issues"].append(f"step{i} ({cmd}): 缺少动作后战斗快照，终局或截断处未验证")
            continue
        if "BattleContext" not in seg:
            stats["diff"] += 1
            stats["issues"].append(f"step{i} ({cmd}): lightspeed 段无 BattleContext（屏幕不同步？）")
            continue
        try:
            diffs = compare_snapshot(parse_last_bc(seg), snap, unverified)
        except (ValueError, KeyError, TypeError) as exc:
            stats["diff"] += 1
            stats["issues"].append(f"step{i} ({cmd}): 快照解析失败，{exc}")
            continue
        stats["steps"] += 1
        if diffs:
            stats["diff"] += 1
            stats["issues"].append(f"step{i} ({cmd}): " + "; ".join(diffs))
        else:
            stats["pass"] += 1
    stats["unverified"] = sorted(unverified)
    if verbose:
        print(f"  [有限校准] 比较 {stats['steps']} 个战斗步：{stats['pass']} 已记录字段一致 / {stats['diff']} 差异 / "
              f"{stats['skip']} 跳过（命令共 {len(cmds) - 1} 条，输出段 {len(segs)} 段）")
        for issue in stats["issues"]:
            print("   -", issue)
        if unverified:
            print("   未验证字段：" + "、".join(stats["unverified"]))
    return stats


# =============================================================== 教学模拟器校准
# 日志 → 我们自己的 Combat 逐步重放；只比较日志实际提供的字段。
# 种子口径：combat_seed = get_seed_long(seed_ui) + floor（BattleContext::init 公式）。
# 方言处理：日志怪 id FuzzyLouseNormal 无红绿（颜色是运行时 roll），按位置比对，
# 同类实体按位置保留；HP 一致不能单独证明隐藏的颜色信息。

from sts.env.actions import END_TURN  # noqa: E402
from sts.env.combat import Combat  # noqa: E402

OURS_INTENT_CATEGORY = {
    "chomp": "ATTACK", "thrash": "ATTACK_DEFEND", "bellow": "DEFEND_BUFF",
    "incantation": "BUFF", "dark_strike": "ATTACK",
    "bite": "ATTACK", "grow": "BUFF", "spit_web": "DEBUFF",
}

# 当前正在校准的 run 的 RNG 前缀（replay_room_ours 设置，_compare_ours 读取）
ENTER_SEEDS: dict = {}  # 进战斗快照的日志 seeds
OURS_ENTER_RNG: dict = {}  # 进战斗快照的我方消耗


def _encounter_of(log_mons: list[dict]) -> str | None:
    kinds = {norm_id(m["id"]) for m in log_mons}
    if kinds == {"JAWWORM"}:
        return "jaw_worm"
    if kinds == {"CULTIST"}:
        return "cultist"
    if all(k.startswith("FUZZYLOUSE") for k in kinds) and len(log_mons) == 2:
        return "louses"
    return None


def _ours_snap(combat: Combat) -> dict:
    """我们侧快照，字段语义对齐日志快照。"""
    s = combat.state
    return {
        "monsters": [
            {"id": e.kind, "hp": e.hp, "hp_max": e.hp_max, "block": e.block,
             "intent": e.intent, "alive": e.alive}
            for e in s.enemies
        ],
        "player": {"hp": s.player.hp, "hp_max": s.player.hp_max,
                   "energy": s.player.energy, "block": s.player.block},
        "piles": {"hand": list(s.hand), "drawPile": list(s.draw_pile),
                  "discardPile": list(s.discard_pile)},
        "rng": s.rng.consumption(),
    }


def _compare_ours(ours: dict, snap: dict, draw_dir: str,
                  unverified: set[str] | None = None) -> list[str]:
    """我们快照 vs 日志快照（同一步），返回差异清单。"""
    diffs: list[str] = []
    if unverified is None:
        unverified = set()
    lc = snap.get("combat_state", {})
    log_mons = lc.get("monsters", [])
    if len(log_mons) != len(ours["monsters"]):
        diffs.append(f"怪物数: 我们 {len(ours['monsters'])} vs 日志 {len(log_mons)}")
    for i, (lm, om) in enumerate(zip(log_mons, ours["monsters"])):
        # 死亡怪日志记 0、我方可能为负：两侧都按「死亡即 0」口径比对
        ours_hp = max(0, om["hp"]) if not om["alive"] else om["hp"]
        log_hp = max(0, lm["hp_current"])
        if (log_hp, lm["hp_max"]) != (ours_hp, om["hp_max"]):
            diffs.append(f"monster[{i}].hp: 日志 {lm['hp_current']}/{lm['hp_max']} vs 我们 {om['hp']}/{om['hp_max']}")
        log_dead = lm.get("is_gone") or lm["hp_current"] == 0
        if log_dead != (not om["alive"]):
            diffs.append(f"monster[{i}].alive: 日志 {'死' if log_dead else '活'} vs 我们 {'活' if om['alive'] else '死'}")
        log_intent = lm.get("intent")
        if log_intent and om["intent"]:
            mapped = OURS_INTENT_CATEGORY.get(om["intent"])
            if mapped is None:
                unverified.add(f"monster[{i}].intent（未收录映射 {om['intent']}）")
            elif mapped != log_intent:
                diffs.append(f"monster[{i}].intent: 日志 {log_intent} vs 我们 {om['intent']}({mapped})")
        else:
            unverified.add(f"monster[{i}].intent")
        _compare_status(om, lm, f"monster[{i}]", diffs, unverified, "我们")
    _compare_player(ours["player"], snap, diffs, unverified, "我们")
    for log_key, our_key in (("hand", "hand"), ("draw_pile", "drawPile"), ("discard_pile", "discardPile")):
        if log_key not in lc:
            unverified.add(our_key)
            continue
        mapped = map_pile(lc[log_key])
        if any(c is None for c in mapped):
            unverified.add(f"{our_key}（含未收录卡名）")
            continue
        ours_cards = ours["piles"][our_key]
        if our_key == "drawPile" and draw_dir == "back":
            mapped = mapped[::-1]
        if mapped != ours_cards:
            diffs.append(f"{our_key}: 日志 {mapped} vs 我们 {ours_cards}")
    # RNG 计数：比较「相对进战斗快照」的增量，消除 run 级前缀（misc 等）
    log_seeds = snap.get("seeds", {})
    stream_map = {"shuffle": "shuffle", "ai": "enemy_ai", "monster_hp": "enemy_roll", "misc": "misc"}
    for k_log, k_ours in stream_map.items():
        if k_log not in log_seeds or k_log not in ENTER_SEEDS:
            continue
        delta = log_seeds[k_log] - ENTER_SEEDS[k_log]
        ours_delta = ours["rng"].get(k_ours, 0) - OURS_ENTER_RNG.get(k_ours, 0)
        if delta != ours_delta:
            diffs.append(f"rng.{k_ours}: 日志增量 {delta} vs 我们增量 {ours_delta}")
    return diffs


def replay_room_ours(run: dict, verbose: bool = True) -> dict | None:
    """把日志里的第一场战斗在自写模拟器重放，逐步对拍日志快照。"""
    battles = [f for f in run["floors"] if "combat_state" in f]
    if not battles:
        return None
    enter = battles[0]
    lc = enter["combat_state"]

    encounter = _encounter_of(lc["monsters"])
    if encounter is None:
        if verbose:
            print(f"  [教学环境有限校准] 遭遇 {lc['monsters']} 不在切片范围，跳过")
        return None

    sys.path.insert(0, BUILD_DIR)
    import importlib

    lss = importlib.import_module("slaythespire")
    combat_seed = lss.get_seed_long(run["seed_ui"]) + enter["floor"]

    p0 = lc["player"]
    if len(lc["hand"]) != 5 or p0.get("energy", 3) != 3 or p0.get("block", 0) != 0:
        if verbose:
            print(f"  [教学环境有限校准] 非标准开局（hand={len(lc['hand'])}, energy={p0.get('energy')}, "
                  f"block={p0.get('block')}），跳过")
        return None
    if any(m["hp_current"] != m["hp_max"] for m in lc["monsters"]):
        if verbose:
            print(f"  [教学环境有限校准] 怪物非满血（1 血祝福？），跳过")
        return None

    combat = Combat(encounter=encounter, seed=combat_seed)
    combat.reset()
    combat.state.player.hp = enter["hp_current"]
    combat.state.player.hp_max = enter["hp_max"]

    draw_dir = "front"
    ours_enter = _ours_snap(combat)
    if ours_enter["piles"]["drawPile"] != map_pile(lc["draw_pile"]):
        draw_dir = "back"
    global ENTER_SEEDS, OURS_ENTER_RNG
    ENTER_SEEDS = enter.get("seeds", {})
    OURS_ENTER_RNG = dict(ours_enter["rng"])

    stats = {"steps": 0, "pass": 0, "diff": 0, "skip": 0, "issues": [], "unverified": []}
    unverified: set[str] = set()

    def check(ours: dict, snap: dict, tag: str) -> None:
        diffs = _compare_ours(ours, snap, draw_dir, unverified)
        stats["steps"] += 1
        if diffs:
            stats["diff"] += 1
            stats["issues"].append(f"{tag}: " + "; ".join(diffs))
        else:
            stats["pass"] += 1

    check(ours_enter, enter, "enter")

    for ev in run["events"]:
        if ev["_order"] < enter["_order"]:
            continue
        if ev["_type"] == "action:play_card":
            action = ev["card_index"] * 3 + ev.get("target_index", 0)
            if not combat.done:
                combat.step(action)
        elif ev["_type"] == "action:end_turn":
            if not combat.done:
                combat.step(END_TURN)
        elif ev["_type"] in ("action:select_reward", "action:select_card"):
            break  # 战斗结束进入奖励，教学环境校准段结束
        else:
            continue
        snap = snapshot_after(run, ev["_order"])
        if snap is None:
            stats["skip"] += 1  # 文件截断处（未归档局）
            stats["issues"].append(f"step{ev['_order']}: 缺少动作后战斗快照，终局或截断处未验证")
            continue
        check(_ours_snap(combat), snap, f"step{ev['_order']}")

    stats["unverified"] = sorted(unverified)
    if verbose:
        print(f"  [教学环境有限校准] 遭遇={encounter}, combat_seed={combat_seed}："
              f"{stats['steps']} 快照，{stats['pass']} 已记录字段一致 / {stats['diff']} 差异 / {stats['skip']} 缺快照跳过"
              f"（draw_pile 方向={draw_dir}）")
        for issue in stats["issues"]:
            print("   -", issue)
        if unverified:
            print("   未验证字段：" + "、".join(stats["unverified"]))
    return stats


def replay_file(path: str) -> dict:
    run = parse_runlog(path)
    print(f"== {os.path.basename(path)} ==")
    print(f"  seed={run['seed_ui']} 职业={run['class']} 进阶={run['ascension']} mods={sorted(run['mods'])}")
    ls_stats = replay_log(run)
    battles = [f for f in run["floors"] if "combat_state" in f]
    ours_stats = replay_room_ours(run) if battles else None
    return {"lightspeed": ls_stats, "ours": ours_stats}


def main(argv: list[str] | None = None) -> int:
    paths = sys.argv[1:] if argv is None else argv
    if not paths:
        paths = sorted(glob.glob(os.path.join(RUNLOGS_DIR, "*", "*.run.log")), key=os.path.getmtime)
    if not paths:
        print("没有日志可比较，本次不能判定校准通过。")
        return 1
    failed = False
    for path in paths:
        try:
            results = replay_file(path)
        except (OSError, RuntimeError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
            print(f"{path}: 校准失败，{exc}")
            failed = True
            continue
        for stats in results.values():
            if stats is not None and (stats["diff"] or stats["pass"] == 0):
                failed = True
    print("以上仅为已有日志的有限校准；缺失字段及终局未验证，不据此宣称全量通过。")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
