"""运行 D25 S2 并保存固定数据、曲线、权重和可复现的源码快照。"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
import zipfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
import yaml

from sts.env.lightspeed import _load_backend
from sts.models.mlp import batch_flat_inputs, load_mlp_checkpoint, save_mlp_checkpoint
from sts.models.overfit import (
    OverfitConfig,
    collect_dataset,
    serialize_dataset,
    train_overfit,
    validate_dataset,
    weight_hash,
)
from sts.rewards import BATTLE_REWARD_CONTRACT

ROOT = Path(__file__).resolve().parents[1]


def snapshot_sources(directory: Path) -> dict:
    """未提交的代码也按字节归档，保存内容哈希以重建本次实验。"""

    paths = [
        ROOT / name
        for name in (
            "pyproject.toml",
            "archive/spec-v4.md",
            "archive/spec-v5.md",
            "spec-v6.md",
            "eval_seeds.json",
            "AGENTS.md",
        )
    ]
    for folder in ("sts", "scripts", "tests", "patches"):
        paths.extend(path for path in (ROOT / folder).rglob("*") if path.suffix in {".py", ".json", ".patch", ".ps1", ".bat"})
    paths.extend(ROOT / "docs" / name for name in ("decisions.md", "mlp-smoke-plan.md"))
    manifest = {}
    with zipfile.ZipFile(directory / "source.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            data = path.read_bytes()
            name = path.relative_to(ROOT).as_posix()
            manifest[name] = hashlib.sha256(data).hexdigest()
            archive.writestr(name, data)
    return {
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).strip(),
        "source_manifest": manifest,
        "source_archive_sha256": hashlib.sha256((directory / "source.zip").read_bytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "runs" / f"mlp-overfit-{datetime.now().astimezone():%Y%m%d-%H%M%S}",
    )
    parser.add_argument("--updates", type=int, default=1500)
    args = parser.parse_args()
    config = OverfitConfig(updates=args.updates)
    directory = args.output_dir.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model_seeds = (500_000, 500_001, 500_002)
    started = time.perf_counter()
    metadata = snapshot_sources(directory)
    backend = Path(_load_backend().__file__)
    metadata.update({
        **BATTLE_REWARD_CONTRACT.to_dict(),
        "timestamp": datetime.now().astimezone().isoformat(), "python": sys.version,
        "platform": platform.platform(), "torch": str(torch.__version__), "numpy": np.__version__, "device": "cpu",
        "threads": torch.get_num_threads(), "deterministic_algorithms": True,
        "eval_seeds_sha256": hashlib.sha256((ROOT / "eval_seeds.json").read_bytes()).hexdigest(),
        "backend_sha256": hashlib.sha256(backend.read_bytes()).hexdigest(),
    })
    (directory / "config.yaml").write_text(yaml.safe_dump({
        "experiment": "D25-S2-v6-contract",
        "config": asdict(config),
        "reward_contract": BATTLE_REWARD_CONTRACT.to_dict(),
        "model_seeds": list(model_seeds),
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    samples, pairs, episodes = collect_dataset(config)
    dataset = serialize_dataset(samples, pairs, episodes)
    (directory / "dataset.json").write_bytes(dataset)
    metadata["dataset_sha256"] = hashlib.sha256(dataset).hexdigest()
    batch = batch_flat_inputs([sample["observation"] for sample in samples])
    repetitions = []
    for model_seed in model_seeds:
        model, result = train_overfit(samples, pairs, config, model_seed)
        result["weight_sha256"] = weight_hash(model)
        checkpoint = directory / f"model-{model_seed}.pt"
        save_mlp_checkpoint(checkpoint, model, extra={
            "purpose": "S2 同批记忆诊断，不能作为 PPO 成绩", "dataset_sha256": metadata["dataset_sha256"],
            "model_seed": model_seed,
            "updates": config.updates,
            "reward_contract": BATTLE_REWARD_CONTRACT.to_dict(),
        })
        restored, _ = load_mlp_checkpoint(checkpoint)
        with torch.no_grad():
            result["checkpoint_equal"] = all(torch.equal(left, right) for left, right in zip(model(batch), restored(batch)))
        result["passed"] &= result["checkpoint_equal"]
        repetitions.append(result)
        print(json.dumps({"seed": model_seed, "final": result["history"][-1], "passed": result["passed"]}, ensure_ascii=False), flush=True)
    regenerated = serialize_dataset(*collect_dataset(config))
    replay_model, replay = train_overfit(samples, pairs, config, model_seeds[0])
    determinism = {
        "dataset_equal": regenerated == dataset,
        "weights_equal": weight_hash(replay_model) == repetitions[0]["weight_sha256"],
        "metrics_equal": replay["history"] == repetitions[0]["history"],
    }
    report = {
        "metadata": metadata, "config": asdict(config),
        "dataset": validate_dataset(samples, pairs), "repetitions": repetitions,
        "determinism": determinism, "elapsed_seconds": time.perf_counter() - started,
        "passed": all(item["passed"] for item in repetitions) and all(determinism.values()),
    }
    (directory / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(directory / "report.json"), "passed": report["passed"], "determinism": determinism}, ensure_ascii=False), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
