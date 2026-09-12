"""真实中途卡组与自主战斗配置；来源身份只进入运行元数据。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sts.env.public_battle import CONTRACT_HASH, _canonical

BATCH_PATH = Path(__file__).with_name("real-deck-batch.json")
POLICY = "real-deck-configured-battle-v1"


def load_batch(path=BATCH_PATH):
    batch = json.loads(Path(path).read_text(encoding="utf-8"))
    payload = {k: v for k, v in batch.items() if k != "payload_sha256"}
    if hashlib.sha256(_canonical(payload)).hexdigest() != batch.get("payload_sha256"):
        raise ValueError("真实卡组批次整体哈希不匹配")
    if batch.get("schema") != "real-deck-batch-v1" or batch.get("source_admission_policy") != POLICY:
        raise ValueError("真实卡组批次版本不匹配")
    if batch.get("contract_sha256") != CONTRACT_HASH:
        raise ValueError("真实卡组批次与当前内容契约不匹配")
    groups, ids = {}, set()
    for row in batch["decks"]:
        if row["deck_id"] in ids or row["split"] not in {"train", "development"}:
            raise ValueError("重复卡组身份或未知划分")
        ids.add(row["deck_id"])
        if row["group_id"] in groups and groups[row["group_id"]] != row["split"]:
            raise ValueError("同源卡组跨划分")
        groups[row["group_id"]] = row["split"]
    return batch


def configured_scene(batch, deck_id, profile_id, encounter):
    row = next((r for r in batch["decks"] if r["deck_id"] == deck_id), None)
    profile = batch["profiles"].get(profile_id)
    if row is None or profile is None or encounter not in batch["encounters"]:
        raise ValueError("卡组、条件或遭遇不在冻结批次")
    candidate = {**batch["common"], **profile, "deck": row["deck"], "encounter": encounter}
    # 每次独立复制，调用方修改不能污染其他场景。
    candidate = json.loads(json.dumps(candidate))
    return {
        "source_admission_policy": POLICY, "batch_sha256": batch["payload_sha256"],
        "scene_id": f"{deck_id}:{profile_id}:{encounter}", "deck_id": deck_id,
        "profile_id": profile_id, "encounter": encounter, "group_id": row["group_id"],
        "research_split": row["split"], "snapshot_type": "verified_intermediate_deck",
        "source_path": row["source_path"], "raw_sha256": row["raw_sha256"],
        "source_scene_ids": row["source_scene_ids"],
        "content_admission_status": "accepted", "content_blockers": [], "candidate": candidate,
        "candidate_sha256": hashlib.sha256(_canonical(candidate)).hexdigest(),
    }


def validate_configured_scene(scene, purpose):
    batch = load_batch()
    expected = configured_scene(batch, scene.get("deck_id"), scene.get("profile_id"), scene.get("encounter"))
    if dict(scene) != expected:
        raise ValueError("配置场景与冻结批次不一致")
    if purpose == "evaluation":
        raise ValueError("该批已用于开发，尚无未触碰的正式保留评估集")
    if purpose == "train" and expected["research_split"] != "train":
        raise ValueError("开发卡组不得用于训练采样")
    return expected["candidate"], {
        k: v for k, v in expected.items() if k not in {"candidate", "content_blockers", "content_admission_status"}
    }


def sample_scene(batch, rng, split="train"):
    """按run、组内卡组、条件和遭遇逐级均匀采样，rng由采集器独立持有。"""
    rows = [r for r in batch["decks"] if r["split"] == split]
    groups = sorted({r["group_id"] for r in rows})
    if not groups:
        raise ValueError("指定划分没有卡组")
    group = groups[int(rng.integers(len(groups)))]
    choices = [r for r in rows if r["group_id"] == group]
    row = choices[int(rng.integers(len(choices)))]
    profiles = sorted(batch["profiles"])
    return configured_scene(batch, row["deck_id"], profiles[int(rng.integers(len(profiles)))],
                            batch["encounters"][int(rng.integers(len(batch["encounters"])))])
