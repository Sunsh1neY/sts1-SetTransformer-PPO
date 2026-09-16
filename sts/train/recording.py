"""训练运行的源码归档与环境指纹；保存未提交文件以支持复现。"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from sts.env.lightspeed import _load_backend
from sts.rewards import (
    BATTLE_REWARD_CONTRACT,
    RewardContract,
    require_reward_contract,
)

ROOT = Path(__file__).resolve().parents[2]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_failure(directory: Path, error: BaseException, phase: str) -> None:
    """仅记录失败与最近完整快照；绝不把半次更新写成可恢复checkpoint。"""

    metrics = directory / "metrics.jsonl"
    last = None
    if metrics.is_file():
        lines = metrics.read_text(encoding="utf-8").splitlines()
        if lines:
            last = json.loads(lines[-1])
    checkpoints = sorted(directory.glob("checkpoint-*.pt"))
    payload = {
        "status": "failed", "phase": phase,
        "error_type": type(error).__name__, "error_message": str(error),
        "last_logged_iteration": last["iteration"] if last else None,
        "last_complete_checkpoint": checkpoints[-1].name if checkpoints else None,
        "training_completed": False,
    }
    (directory / "failure.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_resume_origin(checkpoint: Path) -> dict:
    """续训前核对原run的Python训练语义与评估集；归档时间戳不参与代码比较。"""

    import torch
    original = json.loads((checkpoint.parent / "metadata.json").read_text(encoding="utf-8"))
    reward_fields = set(RewardContract.__dataclass_fields__)
    require_reward_contract({key: original[key] for key in reward_fields if key in original})
    payload = torch.load(checkpoint, weights_only=True, map_location="cpu")
    recorded = payload["extra"]["metadata"]
    if recorded.get("source_archive_sha256") != original["source_archive_sha256"]:
        raise ValueError("checkpoint与原run源码记录不匹配")
    if file_hash(checkpoint.parent / "source.zip") != original["source_archive_sha256"]:
        raise ValueError("原run源码归档损坏")
    if file_hash(ROOT / "eval_seeds.json") != original["eval_seeds_sha256"]:
        raise ValueError("评估种子文件发生变化")
    # recording只负责落盘，不参与训练计算；允许修正日志记录而不改变模型/环境/PPO。
    differences = [name for name, digest in original["source_manifest"].items()
                   if name.startswith("sts/") and name.endswith(".py")
                   and name != "sts/train/recording.py"
                   and (not (ROOT / name).is_file() or file_hash(ROOT / name) != digest)]
    if differences:
        raise ValueError(f"训练代码与原run不一致，请使用源码归档恢复：{differences}")
    return original


def record_metadata(
    directory: Path,
    reward_contract: RewardContract = BATTLE_REWARD_CONTRACT,
) -> dict:
    """纯本地只读采集；产物写入本次新建run目录。"""

    paths = [ROOT / name for name in (
        "pyproject.toml", "spec-v6.md", "eval_seeds.json", "AGENTS.md",
        "archive/spec-v4.md", "archive/spec-v5.md",
    )]
    suffixes = {".py", ".json", ".patch", ".ps1", ".bat", ".yaml", ".txt"}
    for folder in ("sts", "scripts", "tests", "patches", "configs", "licenses"):
        paths.extend(path for path in (ROOT / folder).rglob("*") if path.suffix in suffixes)
    paths.extend(ROOT / "docs" / name for name in ("decisions.md", "mlp-smoke-plan.md", "ppo-source.md"))
    manifest = {}
    with zipfile.ZipFile(directory / "source.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            archive.writestr(name, data)
            manifest[name] = hashlib.sha256(data).hexdigest()
    metadata = {
        "timestamp": datetime.now().astimezone().isoformat(),
        **reward_contract.to_dict(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).strip(),
        "source_manifest": manifest, "source_archive_sha256": file_hash(directory / "source.zip"),
        "eval_seeds_sha256": file_hash(ROOT / "eval_seeds.json"),
        "backend_sha256": file_hash(Path(_load_backend().__file__)),
        "adapter_patch_sha256": file_hash(ROOT / "patches" / "lightspeed-battle-env.patch"),
        "cleanrl_lock": json.loads((ROOT / "scripts" / "cleanrl-lock.json").read_text(encoding="utf-8")),
        "python": sys.version, "platform": platform.platform(), "device": "cpu", "threads": 1,
        "command": [sys.executable, *sys.argv],
        "packages": {name: importlib.metadata.version(name) for name in ("torch", "numpy", "tensorboard", "pyyaml")},
    }
    (directory / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata
