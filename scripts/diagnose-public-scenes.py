"""对完整派生场景做随机/规则集成；不执行正式Gate或PPO训练。"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sts.agents.public_runner import PublicRandomAgent, run_public_episode
from sts.agents.rule_agent import RuleAgent
from sts.env.lightspeed import _load_backend
from sts.env.public_battle import PublicBattleEnv, load_scene_manifest, CONTRACT_HASH


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reference/public-scene-integration.json")
    args = parser.parse_args()
    manifest, scenes = load_scene_manifest()
    module = _load_backend()
    records = []
    for index, scene in enumerate(scenes):
        for policy in ("random", "rule"):
            seed = 910000 + index
            try:
                env = PublicBattleEnv()
                obs = env.reset(scene, seed)
                agent = RuleAgent() if policy == "rule" else PublicRandomAgent(1910000 + index)
                trace = run_public_episode(env, agent, obs)
                record = {"scene_id": scene["scene_id"], "group_id": scene["group_id"],
                          "research_split": scene["research_split"], "policy": policy,
                          "environment_seed": seed, "actions": trace["actions"], "steps": trace["steps"],
                          "total_reward": trace["total_reward"], "terminated": trace["terminated"],
                          "truncated": trace["truncated"], "final_hp": trace["final_observation"]["player"]["hp"],
                          "status": "completed"}
            except Exception as exc:
                record = {"scene_id": scene["scene_id"], "policy": policy, "status": "error", "error": f"{type(exc).__name__}: {exc}"}
            records.append(record)
    summary = {}
    for policy in ("random", "rule"):
        rows = [r for r in records if r["policy"] == policy]
        complete = [r for r in rows if r["status"] == "completed"]
        summary[policy] = {"requested": len(rows), "completed": len(complete), "errors": len(rows) - len(complete),
                           "terminated": sum(r["terminated"] for r in complete), "truncated": sum(r["truncated"] for r in complete),
                           "wins": sum(r["total_reward"] > 0 for r in complete),
                           "mean_reward": sum(r["total_reward"] for r in complete) / len(complete) if complete else None,
                           "actions": sum(r["steps"] for r in complete)}
    result = {"schema": "public-scene-integration-v1", "purpose": "development-integration-not-gate",
              "manifest": manifest, "contract_hash": CONTRACT_HASH,
              "backend_sha256": hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                                ("sts/env/public_battle.py", "sts/agents/rule_agent.py", "sts/agents/public_runner.py")},
              "summary": summary, "records": records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"backend_sha256": result["backend_sha256"], "summary": summary}, ensure_ascii=False, indent=2))
    return int(any(r["status"] != "completed" for r in records))


if __name__ == "__main__":
    raise SystemExit(main())
