"""资源预检后冻结预算，执行统一实体Set两组及配对开发评估。"""
from __future__ import annotations

import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import zipfile

import numpy as np
import torch
from torch.utils.tensorboard import SummaryWriter

from sts.env.unified import load_contract
from sts.env.real_deck import configured_scene, load_batch
from sts.train.unified import UnifiedTrainer as ComparisonTrainer, check_deadline, evaluate, fingerprint

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def cases():
    batch = load_batch()
    result = []
    for row in batch["decks"]:
        if row["split"] != "development":
            continue
        for profile in batch["profiles"]:
            for encounter in batch["encounters"]:
                scene = configured_scene(batch, row["deck_id"], profile, encounter)
                result.append({"case_id": scene["scene_id"], "scene": scene, "seed": 970000 + len(result)})
    return result


def paired(before, after):
    """先按来源run平均，再进行组级bootstrap；截断用回报上下界而非失败0。"""
    b = {r["case_id"]: r for r in before}
    grouped = defaultdict(list)
    for a in after:
        old = b[a["case_id"]]
        lo = (a["reward"] if a["reward"] is not None else 0) - (old["reward"] if old["reward"] is not None else 1.5)
        hi = (a["reward"] if a["reward"] is not None else 1.5) - (old["reward"] if old["reward"] is not None else 0)
        grouped[a["group_id"]].append((lo, hi))
    values = np.array([np.mean(rows, axis=0) for _, rows in sorted(grouped.items())])
    rng = np.random.default_rng(850000)
    draws = rng.integers(len(values), size=(5000, len(values)))
    means = values[draws].mean(1)
    interval = [float(np.quantile(means[:, 0], 0.025)), float(np.quantile(means[:, 1], 0.975))]
    return {"group_mean_difference_bounds": values.mean(0).tolist(), "cluster_bootstrap_95_bounds": interval,
            "groups": len(values), "cases": len(after), "improvement_pass": interval[0] > 0,
            "truncated_before": sum(r["truncated"] for r in before), "truncated_after": sum(r["truncated"] for r in after),
            "scope": "fixed-development-groups;not-population-or-training-randomness-CI"}


def preflight(output, device, stop_at):
    if output.exists():
        raise ValueError("预检目录已存在，请使用新目录以保留证据")
    output.mkdir(parents=True)
    results = []
    for kind in ("set",):
        started = time.monotonic()
        trainer = ComparisonTrainer(kind, iterations=5, device=device)
        for _ in range(4):
            metric, episodes = trainer.iteration_step(deadline=started + 600)
            results.append({"kind": kind, **metric})
            print(kind, "preflight", metric["iteration"], round(metric["seconds"], 3), flush=True)
        trainer.save(output / f"{kind}-smoke.pt")
        restored = ComparisonTrainer.load(output / f"{kind}-smoke.pt")
        for k, v in trainer.model.state_dict().items():
            torch.testing.assert_close(v, restored.model.state_dict()[k], rtol=0, atol=0)
        trainer.iteration_step(deadline=started + 600)
        restored.iteration_step(deadline=started + 600)
        for k, v in trainer.model.state_dict().items():
            torch.testing.assert_close(v, restored.model.state_dict()[k], rtol=0, atol=0)
        write(output / f"{kind}-smoke.json", {"parameters": sum(p.numel() for p in trainer.model.parameters()),
              "peak_cuda_bytes": torch.cuda.max_memory_allocated() if device == "cuda" else 0})
    # 两组等步数；按剩余空闲窗扣除20分钟评估/保存后，加60%耗时余量。
    slow = max(statistics.mean(r["seconds"] for r in results if r["kind"] == k and r["iteration"] > 1) for k in ("set",))
    remaining = min(14400, stop_at - time.time())
    if remaining < 1500:
        raise ValueError("剩余空闲时间不足以冻结两组训练和评估")
    iterations = max(4, min(4096, int((remaining - 1200) / (2 * slow * 1.6))))
    plan = {"schema": "unified-ppo-plan-v1", "device": device, "iterations_per_run": iterations,
            "num_envs": 8, "num_steps": 64, "transitions_per_run": iterations * 512,
            "runs": [{"kind": kind, "group": group} for kind in ("set",) for group in (0, 1)],
            "formal_seconds_limit": 14400, "stop_at_unix": stop_at,
            "evaluation_save_reserve_seconds": 1200, "throughput_safety_factor": 1.6,
            "contract": load_contract(), "fingerprint": fingerprint(),
            "ppo": {"learning_rate": 0.00025, "anneal_lr": True, "update_epochs": 4, "minibatches": 4,
                    "gamma": 1.0, "gae_lambda": 0.95, "clip": 0.2, "entropy_coef": 0.01,
                    "value_coef": 0.5, "grad_clip": 0.5, "adam_eps": 0.00001},
            "evaluation": {"case_count": len(cases()), "policy": "greedy", "seed_start": 970000,
                           "split": "development", "criterion": "both-runs-final-minus-initial-cluster-CI-lower>0",
                           "truncation": "unknown-full-return-in-[0,1.5];interval-bounds-not-defeat"},
            "retry_limit": 2, "retry_policy": "requires-explicit-hypothesis-and-remaining-global-budget;no-automatic-best-seed-selection",
            "torch_version": torch.__version__, "gpu": torch.cuda.get_device_name() if device == "cuda" else None,
            "preflight": results}
    write(output / "plan.json", plan)
    write(output / "evaluation-cases.json", cases())
    print("FROZEN", iterations, "iterations,", iterations * 512, "transitions per run", flush=True)


def run(plan_path, output):
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan["fingerprint"] != fingerprint() or plan["contract"] != load_contract():
        raise ValueError("预检后源码或契约改变，需重新预检")
    if output.exists():
        raise ValueError("正式目录已存在，拒绝重置时间预算")
    output.mkdir(parents=True)
    started = time.monotonic()
    deadline = min(started + plan["formal_seconds_limit"], started + (plan['stop_at_unix'] - time.time())) - 60
    write(output / "plan.json", plan)
    write(output / "evaluation-cases.json", cases())
    write(output / "summary.json", {"status": "running", "runs": []})
    write(output / "environment.json", {"torch": torch.__version__, "device": plan["device"],
          "python": sys.version, "executable": sys.executable, "cuda": torch.version.cuda,
          "gpu": torch.cuda.get_device_name() if plan["device"] == "cuda" else None,
          "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(), "fingerprint": fingerprint()})
    with zipfile.ZipFile(output / "source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for file in fingerprint():
            if file != "backend":
                archive.write(ROOT / file, file)
        for file in ("patches/lightspeed-battle-env.patch", "scripts/lightspeed-lock.json", "pyproject.toml"):
            archive.write(ROOT / file, file)
    report = {"status": "running", "runs": [], "formal_seconds_limit": plan["formal_seconds_limit"]}
    try:
        for setting in plan["runs"]:
            check_deadline(deadline)
            kind, group = setting["kind"], setting["group"]
            folder = output / f"{kind}-{group}"
            folder.mkdir()
            trainer = ComparisonTrainer(kind, group=group, iterations=plan["iterations_per_run"], device=plan["device"])
            write(folder / "config.json", trainer.config)
            trainer.save(folder / "initial.pt")
            initial = evaluate(trainer.model, cases(), trainer.device, deadline)
            write(folder / "initial-evaluation.json", initial)
            with SummaryWriter(str(folder / "tensorboard")) as writer, (folder / "metrics.jsonl").open("w", encoding="utf-8") as metrics_file, (folder / "episodes.jsonl").open("w", encoding="utf-8") as episode_file:
                while trainer.iteration < plan["iterations_per_run"]:
                    metric, episodes = trainer.iteration_step(deadline)
                    metrics_file.write(json.dumps(metric, ensure_ascii=False, allow_nan=False) + "\n")
                    metrics_file.flush()
                    write(output / "progress.json", {"kind": kind, "group": group, "iteration": trainer.iteration,
                         "iterations_per_run": plan["iterations_per_run"], "actual_env_steps": trainer.env_steps,
                         "remaining_seconds": deadline-time.monotonic(), "metric": metric})
                    for episode in episodes:
                        episode_file.write(json.dumps(episode, ensure_ascii=False) + "\n")
                    for key, value in metric.items():
                        if value is not None:
                            writer.add_scalar(key, value, metric["steps"])
                    if trainer.iteration % 8 == 0 or trainer.iteration == 1:
                        print(kind, group, "iteration", trainer.iteration, "steps", metric["steps"], "remaining", round(deadline - time.monotonic()), flush=True)
                    if trainer.iteration % 32 == 0:
                        trainer.save(folder / "latest.pt")
            trainer.save(folder / "final.pt")
            restored = ComparisonTrainer.load(folder / "final.pt")
            for key, value in trainer.model.state_dict().items():
                torch.testing.assert_close(value, restored.model.state_dict()[key], rtol=0, atol=0)
            write(folder / "restore-verification.json", {"passed": True, "actual_env_steps": restored.env_steps})
            del restored
            final = evaluate(trainer.model, cases(), trainer.device, deadline)
            write(folder / "final-evaluation.json", final)
            result = {"kind": kind, "group": group, "iterations": trainer.iteration,
                      "transitions": trainer.iteration * 512, "learning": paired(initial, final)}
            report["runs"].append(result)
            write(folder / "result.json", result)
            write(output / "summary.json", report)
            print("RUN COMPLETE", kind, group, json.dumps(result["learning"]), flush=True)
        report["status"] = "complete"
    except Exception as exc:
        report["status"] = "budget_exhausted" if isinstance(exc, TimeoutError) else "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        if "trainer" in locals():
            report["interrupted_run"] = {"kind": kind, "group": group, "actual_env_steps": trainer.env_steps, "phase": trainer.phase}
            trainer.save(folder / "interrupted.pt")
        raise
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        write(output / "summary.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["preflight", "run"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--stop-at", type=float, help="用户空闲窗口结束的Unix秒；预检必填")
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    if args.mode == "preflight":
        if args.stop_at is None:
            parser.error("预检必须指定用户空闲窗口结束时间")
        preflight(args.output, args.device, args.stop_at)
    else:
        if args.plan is None:
            parser.error("正式运行需要冻结plan")
        run(args.plan, args.output)
