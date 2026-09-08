"""用确定性重放审计旧 battle episode 与 v6 奖励契约的兼容性。"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import yaml

from sts import Encounter, LightspeedBattleEnv
from sts.rewards import BATTLE_REWARD_CONTRACT, recompute_episode_reward_and_rtg

ROOT = Path(__file__).resolve().parents[1]


def _load_max_turns(episode_path: Path) -> int:
    config_path = episode_path.parent / "config.yaml"
    if not config_path.is_file():
        raise ValueError(f"缺少原运行配置，不能猜 max_turns：{config_path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    value = config.get("training", {}).get("max_turns")
    if type(value) is not int or value <= 0:
        raise ValueError(f"原运行配置没有有效 max_turns：{config_path}")
    return value


def audit_episode_file(path: Path) -> dict[str, Any]:
    max_turns = _load_max_turns(path)
    env = LightspeedBattleEnv(max_turns=max_turns)
    counts = {"episodes": 0, "wins": 0, "losses": 0, "hard_timeouts": 0}
    failures: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            actions = row["actions"]
            if not isinstance(actions, list) or not actions:
                raise ValueError("actions 必须是非空列表")
            env.reset(row["seed"], Encounter(row["encounter"]))
            rewards = []
            for index, action in enumerate(actions):
                _, reward, terminated, truncated, info = env.step(action)
                rewards.append(reward)
                if (terminated or truncated) != (index == len(actions) - 1):
                    raise ValueError("终局位置与动作序列末尾不一致")
            if not terminated or truncated:
                raise ValueError("旧记录不是完整真终止 battle episode")
            if bool(row["won"]) != bool(info["battle_won"]):
                raise ValueError("旧 won 与重放 battle_won 不一致")
            if int(row["hp"]) != int(info["player_hp"]):
                raise ValueError("旧退出 HP 与重放不一致")
            if "max_hp" in row and int(row["max_hp"]) != int(info["player_max_hp"]):
                raise ValueError("旧 max_hp 与重放不一致")
            if not math.isclose(
                float(row["total_reward"]), sum(rewards), rel_tol=1e-6, abs_tol=1e-6
            ):
                raise ValueError("旧总回报与重放逐步奖励不一致")
            recomputed, rtg = recompute_episode_reward_and_rtg(
                step_count=len(actions),
                task_type="battle",
                task_outcome=info["task_outcome"],
                terminated=True,
                truncated=False,
                hp_exit=info["player_hp"],
                max_hp_exit=info["player_max_hp"],
            )
            if len(rtg) != len(actions) or any(
                not math.isclose(left, right, rel_tol=1e-6, abs_tol=1e-6)
                for left, right in zip(rewards, recomputed)
            ):
                raise ValueError("共享重算入口与环境逐步奖励不一致")
            counts["episodes"] += 1
            if info["battle_won"]:
                counts["wins"] += 1
            else:
                counts["losses"] += 1
            counts["hard_timeouts"] += int(info["task_outcome"] == "hard_timeout")
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            if len(failures) < 10:
                failures.append(f"line={line_number}: {type(error).__name__}: {error}")
    metadata_path = path.parent / "metadata.json"
    metadata = (
        json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata_path.is_file()
        else {}
    )
    required = set(BATTLE_REWARD_CONTRACT.to_dict())
    return {
        "path": str(path.resolve()),
        "max_turns": max_turns,
        **counts,
        "failures": failures,
        "compatible": not failures and counts["episodes"] > 0,
        "numeric_compatibility_verified_by": "deterministic-action-replay",
        "legacy_metadata_missing": sorted(required - set(metadata)),
        "compatible_reward_contract": BATTLE_REWARD_CONTRACT.to_dict(),
        "eligible_as_run_labels": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    paths = args.paths or sorted((ROOT / "runs").glob("*/episodes.jsonl"))
    if not paths:
        parser.error("没有找到 episodes.jsonl")
    files = [audit_episode_file(path.resolve()) for path in paths]
    report = {
        "document_version": "v6",
        "scope": "legacy-battle-data-compatibility",
        "files": files,
        "passed": all(item["compatible"] for item in files),
        "note": "数值兼容不补写旧元数据；旧 battle 数据不得改标为 run 成功标签",
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
