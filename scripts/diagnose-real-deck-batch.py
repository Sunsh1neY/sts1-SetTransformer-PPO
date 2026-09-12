"""新正式reset入口的真实卡组×条件×遭遇开发诊断，不作Gate评估。"""
import hashlib
import json
from collections import Counter
from pathlib import Path

from sts.agents.public_runner import PublicRandomAgent, run_public_episode
from sts.agents.rule_agent import RuleAgent
from sts.env.public_battle import PublicBattleEnv
from sts.env.real_deck import configured_scene, load_batch

ROOT = Path(__file__).resolve().parents[1]


def main():
    batch = load_batch()
    unique = {}
    for row in batch["decks"]:
        unique.setdefault(row["deck_sha256"], row)
    results = []
    for row in unique.values():
        for profile in batch["profiles"]:
            for encounter in batch["encounters"]:
                scene = configured_scene(batch, row["deck_id"], profile, encounter)
                seed = 940000 + len(results) // 2
                for name in ("random", "rule"):
                    result = {"scene_id": scene["scene_id"], "agent": name, "environment_seed": seed}
                    try:
                        env = PublicBattleEnv()
                        obs = env.reset(scene, seed)
                        trace = run_public_episode(env, PublicRandomAgent(seed + 1000000) if name == "random" else RuleAgent(), obs)
                        result.update({k: trace[k] for k in ("steps", "total_reward", "terminated", "truncated")})
                        result["scene_kind"] = trace["final_info"]["scene_kind"]
                    except Exception as exc:
                        result["error"] = f"{type(exc).__name__}: {exc}"
                    results.append(result)
    summary = {name: {"episodes": len(rows), "errors": sum("error" in r for r in rows),
                      "terminated": sum(r.get("terminated", False) for r in rows),
                      "truncated": sum(r.get("truncated", False) for r in rows),
                      "wins": sum(r.get("total_reward", 0) > 0 for r in rows),
                      "mean_reward": sum(r.get("total_reward", 0) for r in rows if "error" not in r) / max(1, sum("error" not in r for r in rows))}
               for name in ("random", "rule") if (rows := [r for r in results if r["agent"] == name])}
    output = {"batch_sha256": batch["payload_sha256"], "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "purpose": "development-integration;not-Gate", "summary": summary, "results": results}
    path = ROOT / "reference/real-deck-integration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    if any("error" in r for r in results):
        print(Counter(r["error"] for r in results if "error" in r))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
