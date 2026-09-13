"""固定Power Through卡组防守压力探针，检查实体增长与容量截断。"""
import json
from pathlib import Path

from sts.env.comparison import ComparisonEnv, card_count
from sts.env.real_deck import configured_scene, load_batch


if __name__ == "__main__":
    batch = load_batch()
    row = next(r for r in batch["decks"] if "Power Through" in r["deck"])
    results = []
    for seed in range(985000, 985020):
        env = ComparisonEnv()
        obs = env.reset(configured_scene(batch, row["deck_id"], "full-basic", "THREE_SENTRIES"), seed)
        max_count, max_delta, steps = card_count(obs), 0, 0
        while True:
            previous = card_count(obs)
            # 有意保持哨卫存活；只打防御牌，否则结束回合。
            choices = [(c["block"], i * 5) for i, c in enumerate(obs["hand"])
                       if c["block"] > 0 and obs["action_mask"][i * 5]]
            action = max(choices)[1] if choices else 50
            obs, reward, done, truncated, info = env.step(action)
            max_count = max(max_count, card_count(obs))
            max_delta = max(max_delta, card_count(obs) - previous)
            steps += 1
            if done or truncated:
                results.append({"seed": seed, "steps": steps, "max_count": max_count, "max_delta": max_delta,
                                "terminated": done, "truncated": truncated, "reason": info["termination_reason"]})
                break
    path = Path(__file__).parents[1] / "reference/comparison-capacity-probe.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"episodes": len(results), "max_count": max(r["max_count"] for r in results),
                      "max_delta": max(r["max_delta"] for r in results), "capacity_truncations": sum(r["truncated"] for r in results)}))
