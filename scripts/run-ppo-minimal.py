"""运行固定最小环境PPO，输出TensorBoard、JSON曲线、训练快照和配对开发诊断。"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import torch
import yaml
from torch.utils.tensorboard import SummaryWriter

from sts.eval import evaluate_diagnostic
from sts.models.overfit import weight_hash
from sts.train.ppo import PPOConfig, PPOTrainer
from sts.train.recording import (
    ROOT,
    record_failure,
    record_metadata,
    validate_resume_origin,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "ppo-minimal.yaml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs" / f"ppo-minimal-{datetime.now().astimezone():%Y%m%d-%H%M%S}")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--stop-after-iterations", type=int)
    parser.add_argument("--diagnostic-episodes", type=int, default=100)
    args = parser.parse_args()
    if args.stop_after_iterations is not None and args.stop_after_iterations <= 0:
        parser.error("--stop-after-iterations必须为正整数")
    if args.diagnostic_episodes < 2:
        parser.error("--diagnostic-episodes至少为2")
    config = PPOConfig(**yaml.safe_load(args.config.read_text(encoding="utf-8")))
    if args.resume:
        validate_resume_origin(args.resume.resolve())
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    trainer = PPOTrainer.load(args.resume) if args.resume else PPOTrainer(config)
    if asdict(trainer.config) != asdict(config):
        raise ValueError("恢复配置与原checkpoint不一致，不能静默改变预算或seed")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    metadata = record_metadata(output, config.reward_contract)
    run_config = {
        "experiment": "D25-S3-v6-contract", "training": asdict(config),
        "diagnostic": {"seed_start": 900000, "episodes_per_encounter": args.diagnostic_episodes, "agent_seed_start": 950000, "bootstrap_seed": 960000, "bootstrap_repeats": 10000},
        "resume": str(args.resume.resolve()) if args.resume else None,
    }
    (output / "config.yaml").write_text(yaml.safe_dump(run_config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    initial_weight = weight_hash(trainer.model)
    try:
        before = evaluate_diagnostic(trainer.model, **run_config["diagnostic"])
    except BaseException as error:
        record_failure(output, error, "diagnostic-before")
        raise
    (output / "diagnostic-before.json").write_text(json.dumps(before, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    first_iteration = trainer.iteration
    end_iteration = config.num_iterations
    if args.stop_after_iterations is not None:
        end_iteration = min(end_iteration, first_iteration + args.stop_after_iterations)
    history = []
    started = time.perf_counter()
    writer = SummaryWriter(str(output / "tensorboard"))
    writer.add_text("configuration", yaml.safe_dump(run_config, allow_unicode=True))
    try:
        with (output / "metrics.jsonl").open("w", encoding="utf-8") as log, (output / "episodes.jsonl").open("w", encoding="utf-8") as episode_log:
            while trainer.iteration < end_iteration:
                metrics, episodes = trainer.train_iteration()
                elapsed = time.perf_counter() - started
                metrics["steps_per_second"] = (trainer.iteration - first_iteration) * config.batch_size / elapsed
                history.append(metrics)
                log.write(json.dumps(metrics, ensure_ascii=False, allow_nan=False) + "\n")
                log.flush()
                for episode in episodes:
                    episode_log.write(json.dumps(episode, ensure_ascii=False, allow_nan=False) + "\n")
                episode_log.flush()
                for key, value in metrics.items():
                    if value is not None and key not in {"iteration", "global_step"}:
                        writer.add_scalar(key, value, metrics["global_step"])
                if trainer.iteration % 16 == 0 or trainer.iteration in (1, end_iteration):
                    print(json.dumps(metrics, ensure_ascii=False, allow_nan=False), flush=True)
                if trainer.iteration % 32 == 0 or trainer.iteration == end_iteration:
                    trainer.save(output / f"checkpoint-{trainer.iteration:04d}.pt", metadata={
                        "source_archive_sha256": metadata["source_archive_sha256"],
                        "eval_seeds_sha256": metadata["eval_seeds_sha256"], "backend_sha256": metadata["backend_sha256"],
                    })
    except BaseException as error:
        record_failure(output, error, "training")
        raise
    finally:
        writer.close()
    elapsed = time.perf_counter() - started
    try:
        after = evaluate_diagnostic(trainer.model, **run_config["diagnostic"])
    except BaseException as error:
        record_failure(output, error, "diagnostic-after")
        raise
    (output / "diagnostic-after.json").write_text(json.dumps(after, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    completed = trainer.iteration == config.num_iterations
    summary = {
        "scope": "minimal-v1-development-smoke", "training_completed": completed,
        "first_iteration": first_iteration, "last_iteration": trainer.iteration,
        "initial_weight_sha256": initial_weight, "final_weight_sha256": weight_hash(trainer.model),
        "parameters_changed": initial_weight != weight_hash(trainer.model),
        "elapsed_training_seconds": elapsed,
        "episodes": sum(point["episodes"] for point in history),
        "timeouts": sum(point["timeouts"] for point in history),
        "illegal_actions": sum(point["illegal_actions"] for point in history),
        "before": before["overall"], "after": after["overall"],
        "last_metrics": history[-1] if history else None,
        "eval_seeds_sha256": metadata["eval_seeds_sha256"],
        "note": "S3单初始化开发诊断；不替代中等档Gate3或多训练seed稳健性评估",
    }
    (output / "report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output / "report.json"), **summary}, ensure_ascii=False, allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
