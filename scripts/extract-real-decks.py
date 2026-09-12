"""从固定本地公开语料直接提取最终卡组，不重建历史战斗入口。"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/audit-public-corpus.py"
SPEC = importlib.util.spec_from_file_location("real_deck_corpus", HELPER)
CORPUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORPUS)
CONTRACT = ROOT / "sts/env/public-battle-contract.json"
MAPPINGS = ROOT / "third_party/sts_lightspeed/include/constants/SaveFileMappings.h"
SCHEMA = "real-deck-manifest-v1"
POLICY = "real-deck-configured-battle-v1"


def digest(value):
    """内容哈希不依赖来源数组排列，重复卡由排序后的列表保留。"""
    return hashlib.sha256(CORPUS.canonical(value)).hexdigest()


def parse_card(value):
    """严格读取 metric ID 和升级次数；不做模糊牌名匹配。"""
    if not isinstance(value, str) or value != value.strip():
        raise ValueError("卡牌必须是无首尾空白的字符串")
    match = re.fullmatch(r"([^+]+?)(?:\+([1-9][0-9]*))?", value)
    if not match:
        raise ValueError("卡牌ID或升级后缀无效")
    name, suffix = match.groups()
    upgraded = int(suffix or 0)
    if upgraded > 1 and name != "Searing Blow":
        raise ValueError("普通卡升级次数超过1")
    return {"name": name, "upgrade_level": upgraded}


def extract_group(group, contract, known_cards):
    run = group["run"]
    raw_deck = run.get("master_deck")
    errors, blockers, cards = [], [], []
    if group.get("conflicting_variants"):
        errors.append("SOURCE_IDENTITY_CONFLICT")
    if not isinstance(raw_deck, list) or not raw_deck:
        errors.append("MASTER_DECK_MISSING_OR_EMPTY")
    else:
        for i, value in enumerate(raw_deck):
            try:
                cards.append(parse_card(value))
            except ValueError as exc:
                errors.append(f"CARD_FORMAT:{i}:{exc}")
    if group.get("card_modifier_group_rejected"):
        errors.append("CUSTOM_CARD_MODIFIERS_UNRESOLVED")
    # 标准卡牌语义与历史精确等价分别记录；不根据未知mod清单全局拒绝。
    supported = {c["name"]: c["max_upgrade"] for c in contract["cards"]}
    for card in cards:
        name, level = card["name"], card["upgrade_level"]
        if name not in known_cards:
            errors.append("UNKNOWN_SOURCE_CARD:" + name)
        if name in CORPUS.PERSISTENT_CARDS:
            errors.append("PERMANENT_CARD_VALUE_UNRECORDED:" + name)
        if name not in supported:
            blockers.append("UNSUPPORTED_CARD:" + name)
        elif level > supported[name]:
            blockers.append(f"UNSUPPORTED_UPGRADE:{name}+{level}")
    if len(cards) > contract["capacity"]["max_initial_cards"]:
        blockers.append("INITIAL_DECK_CAPACITY_EXCEEDED")
    raw_valid = isinstance(raw_deck, list) and all(isinstance(c, str) for c in raw_deck)
    errors, blockers = sorted(set(errors)), sorted(set(blockers))
    return {
        "deck_id": group["group_id"] + ":final-master-deck",
        "group_id": group["group_id"], "snapshot_type": "final_master_deck",
        "source_path": group["source_path"], "raw_sha256": group["raw_sha256"],
        "source_aliases": group["aliases"], "source_identity_tokens": group["identity_tokens"],
        "source_build": run.get("build_version"), "source_ascension": run.get("ascension_level"),
        "source_floor_reached": run.get("floor_reached"),
        "source_field": "master_deck", "raw_deck": raw_deck,
        "raw_deck_multiset_sha256": digest(sorted(raw_deck)) if raw_valid else None,
        "cards": cards, "card_count": len(cards),
        "deck_content_sha256": digest(sorted(cards, key=lambda c: (c["name"], c["upgrade_level"]))) if not errors else None,
        "card_modifier_evidence": CORPUS.card_modifier_evidence(run),
        "historical_rules_equivalence": "unverified",
        "extraction_status": "complete" if not errors else "rejected",
        "extraction_blockers": errors, "backend_blockers": blockers,
        "backend_content_status": "supported" if not errors and not blockers else "blocked",
        "runtime_status": "not_run", "training_admission": "pending_config_and_reset",
        "split": "unassigned",
    }


def subset_stats(rows):
    hashes = {r["deck_content_sha256"] for r in rows if r["deck_content_sha256"]}
    base = Counter(CORPUS.BASE)
    def is_basic(row):
        # A10+固有诅咒不算新增构筑；卡牌升级则视为不同卡组。
        deck = Counter(row["raw_deck"])
        deck.pop("AscendersBane", None)
        return deck == base
    nonbasic = [r for r in rows if not is_basic(r)]
    return {
        "run_groups": len(rows), "unique_decks": len(hashes),
        "nonbasic_run_groups": len(nonbasic),
        "nonbasic_unique_decks": len({r["deck_content_sha256"] for r in nonbasic}),
        "card_classes": sorted({c["name"] for r in rows for c in r["cards"]}),
        "card_versions": sorted({f"{c['name']}+{c['upgrade_level']}" for r in rows for c in r["cards"]}),
        "deck_size_histogram": {str(k): v for k, v in sorted(Counter(r["card_count"] for r in rows).items())},
        "upgraded_deck_groups": sum(any(c["upgrade_level"] for c in r["cards"]) for r in rows),
    }


def build(records, contract, known_cards):
    groups = CORPUS.group_records(records)
    rows = [extract_group(g, contract, known_cards) for g in groups]
    complete = [r for r in rows if r["extraction_status"] == "complete"]
    supported = [r for r in rows if r["backend_content_status"] == "supported"]
    blockers = Counter(b for r in complete for b in r["backend_blockers"])
    single_gain = {b: sum(r["backend_blockers"] == [b] for r in complete) for b in blockers}
    joint = Counter(tuple(r["backend_blockers"]) for r in complete if r["backend_blockers"])
    return {
        "schema": SCHEMA, "source_admission_policy": POLICY,
        "source": {"url": CORPUS.SOURCE_URL, "commit": CORPUS.COMMIT, "archive_sha256": CORPUS.ZIP_SHA},
        "mapping_policy": "exact-metric-id-to-locked-standard-card-v1",
        "split_policy": "unassigned;P2-required;old-research-splits-not-inherited",
        "summary": {
            "raw_files": len(records), "run_groups": len(groups),
            "duplicate_alias_files": len(records) - len(groups),
            "extraction_rejected": len(rows) - len(complete),
            "complete": subset_stats(complete), "backend_supported": subset_stats(supported),
            "extraction_blocker_counts": dict(Counter(b for r in rows for b in r["extraction_blockers"])),
            "backend_blocker_priority": [
                {"blocker": b, "affected_run_groups": n, "single_fix_unlocked_groups": single_gain[b]}
                for b, n in blockers.most_common()
            ],
            "joint_blocker_sets": [{"blockers": list(bs), "run_groups": n} for bs, n in joint.most_common()],
        },
        "decks": rows,
    }


def report(result):
    s = result["summary"]
    complete, supported = s["complete"], s["backend_supported"]
    lines = ["# 真实最终卡组提取报告", "", "本报告只验收 P1 数据提取及当前内容兼容性，不代表新 reset、数据划分或 PPO 已完成。", "",
             "## 输入与复现", "", "固定本地 MaT1g3R 语料；直接读取 master_deck，不读取事件前缀、历史药水或火精英身份。", "",
             f"- 来源：{result['source']['url']}", f"- 归档 SHA256：`{CORPUS.ZIP_SHA}`",
             f"- 中央契约 SHA256：`{result['inputs']['contract_sha256']}`",
             "- 复现：`python scripts/extract-real-decks.py`", "- 针对性验证：`python -m pytest -q tests/test_real_decks.py`", "",
             "## 实际结果", "", "| 指标 | 数量 |", "|---|---:|",
             f"| 原始 Ironclad 文件 | {s['raw_files']} |", f"| 去重 run 组 | {s['run_groups']} |",
             f"| 重复别名文件 | {s['duplicate_alias_files']} |", f"| 提取拒绝组 | {s['extraction_rejected']} |",
             f"| 完整提取卡组 / 不同内容 | {complete['run_groups']} / {complete['unique_decks']} |",
             f"| 完整提取中的非基础不同构筑 | {complete['nonbasic_unique_decks']} |",
             f"| 当前内容支持组 / 不同内容 | {supported['run_groups']} / {supported['unique_decks']} |",
             f"| 当前内容支持的非基础不同构筑 | {supported['nonbasic_unique_decks']} |",
             f"| 完整提取卡牌类别 / 版本 | {len(complete['card_classes'])} / {len(complete['card_versions'])} |", "",
             "基础卡组定义为未升级的5 Strike_R、4 Defend_R、1 Bash，允许额外 AscendersBane；不同卡组哈希保留重复数量与升级，忽略原数组次序。", "",
             f"完整提取大小分布：`{json.dumps(complete['deck_size_histogram'], ensure_ascii=False)}`。", "",
             f"当前支持大小分布：`{json.dumps(supported['deck_size_histogram'], ensure_ascii=False)}`。", "",
             "## 内容缺口", "", "影响组数不能相加当作新增可用卡组；只有全部阻塞解除才能使用完整卡组。单项解锁数为静态估计，不替代机制验收。", "",
             "| 缺口 | 影响 run 组 | 只修此项可解锁 |", "|---|---:|---:|"]
    for b in s["backend_blocker_priority"]:
        lines.append(f"| {b['blocker']} | {b['affected_run_groups']} | {b['single_fix_unlocked_groups']} |")
    lines += ["", "### 最接近可运行的五副完整卡组", "",
              "这里只展示最小联合缺口，不把一副卡组的成功当作分布完成。", "",
              "| 来源组 | 张数 | 需共同补齐 |", "|---|---:|---|"]
    nearest = sorted((r for r in result["decks"] if r["extraction_status"] == "complete"),
                     key=lambda r: (len(r["backend_blockers"]), r["group_id"]))[:5]
    for row in nearest:
        lines.append(f"| {row['group_id']} | {row['card_count']} | {'、'.join(row['backend_blockers']) or '无'} |")
    lines += ["", f"提取拒绝原因及组数：`{json.dumps(s['extraction_blocker_counts'], ensure_ascii=False)}`。原始卡牌列表仍完整保留，拒绝表示不能解释完整实例状态，不表示文件读取失败。", "",
              "完整联合缺口、逐组卡组及拒绝原因见 real-deck-manifest.json；提取错误与运行不支持分别记录。", "",
              "## 证据与下一步", "",
              "逐个原文件哈希、别名、run 关联组和来源原始卡组保存在清单。标准卡牌名称严格映射，不模糊替换；缺少完整历史 mod 列表不作为全局拒绝理由，历史行为等价仍未核验。未知永久实例值和非空自定义修饰独立拒绝。", "",
              "没有按玩家输赢筛选，没有删除不支持卡牌，没有把旧入口99场或新场景乘seed记成不同构筑。来源最终卡组可能跨幕；将其配置到第一幕对手属于新训练条件，不代表历史楼层。", "",
              "当前全部 split=unassigned、runtime_status=not_run。P2 需锁配置与来源分组；P3 需正式 reset 准入。若支持构筑不足，优先消费联合缺口决定补哪些机制，不回到历史入口还原。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "reference/public-run-corpus/matiger-fixed.zip")
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs/real-deck-manifest.json")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/real-deck-data-report.md")
    args = parser.parse_args()
    records = CORPUS.load_records(args.archive.read_bytes())
    result = build(records, json.loads(CONTRACT.read_text(encoding="utf-8")), CORPUS.catalog()["CardId"])
    result["inputs"] = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in {
        "extractor_sha256": Path(__file__), "grouping_helper_sha256": HELPER,
        "contract_sha256": CONTRACT, "card_mapping_sha256": MAPPINGS,
    }.items()}
    CORPUS.write_json(args.manifest, result)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report(result), encoding="utf-8")
    print(json.dumps({k: result["summary"][k] for k in ("raw_files", "run_groups", "extraction_rejected")}, ensure_ascii=False))
    for name in ("complete", "backend_supported"):
        print(name, result["summary"][name]["run_groups"], result["summary"][name]["unique_decks"])


if __name__ == "__main__":
    main()
