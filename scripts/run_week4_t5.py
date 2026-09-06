"""Week 4 T5：正式后端四条完整路径的稳定性、确定性与性能验收。"""

from __future__ import annotations

# 必须在导入 NumPy 前限制常见数值库线程，避免把多线程成绩记成单核吞吐。
import os

for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_name] = "1"

import argparse
import hashlib
import json
import math
import platform
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from sts.agents.episode_runner import decode_agent_decision
from sts.agents.masked_policy import MaskedRandomAgent
from sts.env.lightspeed import (
    ACTION_COUNT,
    Encounter,
    LightspeedBattleEnv,
    _load_backend,
    _observation_to_dict,
)
from sts.env.wrappers import FlattenWrapper, TokenWrapper
from sts.env.registry import DEFAULT_CARD_REGISTRY, SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN = Path(r"C:\msys64\mingw64\bin")
PATH_NAMES = ("raw-pybind", "dict", "flatten", "token")
ENCOUNTER_COUNTS = (
    (Encounter.JAW_WORM, 3334),
    (Encounter.CULTIST, 3333),
    (Encounter.TWO_LOUSE, 3333),
)
SERIALIZATION_VERSION = 2
# `info.outcome` 来自 BattleContext::Outcome，不是绑定层另一个 GameOutcome 枚举。
VICTORY_OUTCOME = 1
LOSS_OUTCOME = 2


@dataclass(frozen=True)
class EpisodeConfig:
    index: int
    seed: int
    encounter: Encounter
    agent_seed: int


@dataclass
class BucketStats:
    episodes: int = 0
    steps: int = 0
    wins: int = 0
    losses: int = 0
    exceptions: int = 0
    illegal_actions: int = 0
    decisions: int = 0
    hard_timeouts: int = 0
    reward_failures: int = 0
    total_reward: float = 0.0
    elapsed_seconds: float = 0.0

    def add(self, other: "BucketStats") -> None:
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(self, name) + getattr(other, name))

    def report(self) -> dict[str, Any]:
        result = asdict(self)
        result["illegal_action_rate"] = (
            self.illegal_actions / self.decisions if self.decisions else 0.0
        )
        result["hard_timeout_rate"] = (
            self.hard_timeouts / self.episodes if self.episodes else 0.0
        )
        result["reward_contract_ok"] = self.reward_failures == 0
        result["steps_per_second"] = (
            self.steps / self.elapsed_seconds if self.elapsed_seconds else 0.0
        )
        return result


@dataclass
class PathRun:
    path: str
    elapsed_seconds: float
    total: BucketStats
    by_encounter: dict[str, BucketStats]
    exception_samples: list[str] = field(default_factory=list)

    def report(self) -> dict[str, Any]:
        total = self.total.report()
        total["elapsed_seconds"] = self.elapsed_seconds
        total["steps_per_second"] = (
            self.total.steps / self.elapsed_seconds if self.elapsed_seconds else 0.0
        )
        return {
            "path": self.path,
            "total": total,
            "by_encounter": {
                name: stats.report() for name, stats in self.by_encounter.items()
            },
            "exception_samples": self.exception_samples,
        }


class PathDriver:
    """把四种环境外观收敛到同一验收控制流，不参与动作选择。"""

    def __init__(self, path_name: str, max_turns: int = 50) -> None:
        self.path_name = path_name
        self.backend = _load_backend()
        self.raw_env: Any | None = None
        self.dict_env: LightspeedBattleEnv | None = None
        if path_name == "raw-pybind":
            self.raw_env = self.backend.IroncladBattleEnv(
                max_turns=max_turns,
                gamma=1.0,
            )
            self.env = self.raw_env
        else:
            self.dict_env = LightspeedBattleEnv(max_turns=max_turns, gamma=1.0)
            if path_name == "dict":
                self.env = self.dict_env
            elif path_name == "flatten":
                self.env = FlattenWrapper(self.dict_env)
            elif path_name == "token":
                self.env = TokenWrapper(self.dict_env)
            else:
                raise ValueError(f"未知路径 {path_name!r}")

    def _backend_encounter(self, encounter: Encounter) -> Any:
        names = {
            Encounter.JAW_WORM: "JAW_WORM",
            Encounter.CULTIST: "CULTIST",
            Encounter.TWO_LOUSE: "TWO_LOUSE",
        }
        return getattr(self.backend.MonsterEncounter, names[encounter])

    def reset(self, config: EpisodeConfig) -> Any:
        if self.raw_env is not None:
            return self.raw_env.reset(
                config.seed,
                self._backend_encounter(config.encounter),
                0,
            )
        return self.env.reset(config.seed, config.encounter, 0)

    def step(self, action: int) -> tuple[Any, float, bool, bool, dict[str, int]]:
        if self.raw_env is not None:
            result = self.raw_env.step(action)
            return (
                result.observation,
                float(result.reward),
                bool(result.terminated),
                bool(result.truncated),
                {str(key): int(value) for key, value in result.info.items()},
            )
        return self.env.step(action)

    def agent_observation(self, observation: Any) -> Mapping[str, Any]:
        if self.raw_env is not None:
            # 这是原始 pybind 路径接入 D23 Agent 所需的唯一转换，也计入秒表。
            return {
                "action_mask": np.asarray(observation.action_mask, dtype=np.bool_)
            }
        return observation

    def semantic_observation(self, observation: Any) -> Mapping[str, np.ndarray[Any, Any]]:
        """得到跨路径可比较的规范语义；只在确定性验收中调用。"""

        if self.raw_env is not None:
            return _observation_to_dict(observation)
        if self.path_name == "dict":
            return observation
        assert self.dict_env is not None
        return self.dict_env.observation()


def build_configs(
    count: int = 10_000,
    seed_start: int = 100_000,
    agent_seed_start: int = 20_260_905_000,
) -> list[EpisodeConfig]:
    """建立唯一配置集；默认严格按 3334/3333/3333 分桶。"""

    if count <= 0:
        raise ValueError("配置数必须为正")
    if seed_start < 100_000:
        raise ValueError("T5 只能使用 seed >= 100000 的训练范围")
    if count == 10_000:
        counts = ENCOUNTER_COUNTS
    else:
        base, remainder = divmod(count, 3)
        encounters = list(Encounter)
        counts = tuple(
            (encounter, base + (1 if index < remainder else 0))
            for index, encounter in enumerate(encounters)
        )
    configs: list[EpisodeConfig] = []
    for encounter, bucket_count in counts:
        for _ in range(bucket_count):
            index = len(configs)
            configs.append(
                EpisodeConfig(
                    index=index,
                    seed=seed_start + index,
                    encounter=encounter,
                    agent_seed=agent_seed_start + index,
                )
            )
    return configs


def _action_mask(observation: Mapping[str, Any]) -> np.ndarray[Any, np.dtype[np.bool_]]:
    mask = np.asarray(observation["action_mask"])
    if mask.shape != (ACTION_COUNT,) or mask.dtype != np.bool_:
        raise TypeError(f"Agent 所见 action_mask 契约错误：{mask.shape}, {mask.dtype}")
    return mask


def _check_reward(
    rewards: Sequence[float],
    terminated: bool,
    truncated: bool,
    info: Mapping[str, int],
) -> bool:
    if not rewards or not terminated or truncated:
        return False
    if any(not math.isfinite(value) for value in rewards):
        return False
    if any(value != 0.0 for value in rewards[:-1]):
        return False
    outcome = int(info.get("outcome", -1))
    if outcome == VICTORY_OUTCOME:
        max_hp = max(1, int(info["player_max_hp"]))
        expected = 1.0 + 0.5 * max(0, int(info["player_hp"])) / max_hp
    elif outcome == LOSS_OUTCOME:
        expected = 0.0
    else:
        return False
    return math.isclose(sum(rewards), expected, rel_tol=1e-6, abs_tol=1e-6)


def run_path(
    path_name: str,
    configs: Sequence[EpisodeConfig],
    max_turns: int = 50,
) -> PathRun:
    """秒表包含 reset、转换、Agent softmax/抽样、校验、step 与记账。"""

    driver = PathDriver(path_name, max_turns=max_turns)
    total = BucketStats()
    by_encounter = {encounter.value: BucketStats() for encounter in Encounter}
    exception_samples: list[str] = []
    start = time.perf_counter()
    for config in configs:
        episode = BucketStats(episodes=1)
        rewards: list[float] = []
        episode_start = time.perf_counter()
        try:
            observation = driver.reset(config)
            agent = MaskedRandomAgent(seed=config.agent_seed)
            terminated = False
            truncated = False
            info: dict[str, int] = {}
            while not (terminated or truncated):
                agent_view = driver.agent_observation(observation)
                mask = _action_mask(agent_view)
                decision = agent.decide(agent_view)
                action = decode_agent_decision(decision)
                episode.decisions += 1
                if not mask[action]:
                    episode.illegal_actions += 1
                observation, reward, terminated, truncated, info = driver.step(action)
                rewards.append(reward)
                episode.steps += 1
            outcome = int(info.get("outcome", -1))
            episode.wins += outcome == VICTORY_OUTCOME
            episode.losses += outcome == LOSS_OUTCOME
            episode.hard_timeouts += int(info.get("timeout", 0) == 1)
            episode.total_reward = float(sum(rewards))
            episode.reward_failures += not _check_reward(
                rewards,
                terminated,
                truncated,
                info,
            )
        except Exception as exc:  # 验收必须继续并分开报告真实异常。
            episode.exceptions += 1
            if len(exception_samples) < 10:
                exception_samples.append(
                    f"config={config.index}, seed={config.seed}, "
                    f"encounter={config.encounter.value}: {type(exc).__name__}: {exc}"
                )
        episode.elapsed_seconds = time.perf_counter() - episode_start
        total.add(episode)
        by_encounter[config.encounter.value].add(episode)
    elapsed = time.perf_counter() - start
    return PathRun(path_name, elapsed, total, by_encounter, exception_samples)


def _canonical_array(array: Any, dtype: str) -> bytes:
    value = np.asarray(array, dtype=np.dtype(dtype), order="C")
    header = json.dumps(
        {"shape": value.shape, "dtype": value.dtype.str},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return len(header).to_bytes(4, "little") + header + value.tobytes(order="C")


def _canonical_cards(cards: Any, name: str) -> bytes:
    """把变长卡牌记录固定为字段明确的二维小端数组。"""

    if not isinstance(cards, list):
        raise TypeError(f"{name} 应为 list")
    rows = []
    for index, card in enumerate(cards):
        if not isinstance(card, Mapping):
            raise TypeError(f"{name}[{index}] 应为卡牌记录")
        rows.append(
            (
                int(card["card_id"]),
                int(card["location"]),
                int(card["target_kind"]),
                int(card["upgraded"]),
                int(card["cost"]),
                int(card["cost_known"]),
            )
        )
    value = np.asarray(rows, dtype="<i4").reshape(len(rows), 6)
    return _canonical_array(value, "<i4")


def serialize_semantic(observation: Mapping[str, Any]) -> bytes:
    """固定字段顺序、dtype 和小端字节序，不含时间或机器元数据。"""

    card_fields = ("hand", "draw_pile", "discard_pile", "exhaust_pile")
    array_fields = (
        ("enemies", "<i4"),
        ("global", "<i4"),
        ("enemy_mask", "|b1"),
        ("action_mask", "|b1"),
    )
    chunks = [f"semantic-v{SERIALIZATION_VERSION}".encode("ascii")]
    for name in card_fields:
        chunks.extend((name.encode("ascii"), _canonical_cards(observation[name], name)))
    for name, dtype in array_fields:
        chunks.extend((name.encode("ascii"), _canonical_array(observation[name], dtype)))
    return b"".join(chunks)


def serialize_path_observation(path_name: str, observation: Any) -> bytes:
    if path_name == "raw-pybind":
        return serialize_semantic(_observation_to_dict(observation))
    if path_name == "dict":
        return serialize_semantic(observation)
    if path_name == "flatten":
        fields = (
            ("card_categorical", "<i8"),
            ("card_numeric", "<f4"),
            ("card_numeric_known", "|b1"),
            ("card_valid", "|b1"),
            ("enemy_features", "<f4"),
            ("enemy_mask", "|b1"),
            ("global", "<f4"),
            ("action_mask", "|b1"),
        )
    elif path_name == "token":
        fields = (
            ("card_categorical", "<i8"),
            ("card_numeric", "<f4"),
            ("card_numeric_known", "|b1"),
            ("card_valid", "|b1"),
            ("enemy_features", "<f4"),
            ("enemy_mask", "|b1"),
            ("global", "<f4"),
            ("action_mask", "|b1"),
        )
    else:
        raise ValueError(path_name)
    chunks = [f"{path_name}-v{SERIALIZATION_VERSION}".encode("ascii")]
    for name, dtype in fields:
        chunks.extend((name.encode("ascii"), _canonical_array(observation[name], dtype)))
    return b"".join(chunks)


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def replay_trace(path_name: str, config: EpisodeConfig) -> list[dict[str, Any]]:
    """逐步保留路径表示、公共语义、完整 mask、动作、奖励、标志与允许 info。"""

    driver = PathDriver(path_name)
    observation = driver.reset(config)
    agent = MaskedRandomAgent(seed=config.agent_seed)
    trace: list[dict[str, Any]] = []
    terminated = False
    truncated = False
    step = 0
    while not (terminated or truncated):
        agent_view = driver.agent_observation(observation)
        mask = _action_mask(agent_view)
        semantic = driver.semantic_observation(observation)
        decision = agent.decide(agent_view)
        action = decode_agent_decision(decision)
        next_observation, reward, terminated, truncated, info = driver.step(action)
        next_agent_view = driver.agent_observation(next_observation)
        next_semantic = driver.semantic_observation(next_observation)
        trace.append(
            {
                "step": step,
                "path_observation_sha256": _digest(
                    serialize_path_observation(path_name, observation)
                ),
                "semantic_observation_sha256": _digest(serialize_semantic(semantic)),
                "action_mask_hex": mask.tobytes().hex(),
                "action": action,
                "next_path_observation_sha256": _digest(
                    serialize_path_observation(path_name, next_observation)
                ),
                "next_semantic_observation_sha256": _digest(
                    serialize_semantic(next_semantic)
                ),
                "next_action_mask_hex": _action_mask(next_agent_view).tobytes().hex(),
                "reward_hex": np.asarray(reward, dtype="<f8").tobytes().hex(),
                "terminated": terminated,
                "truncated": truncated,
                "info": {key: int(info[key]) for key in sorted(info)},
            }
        )
        observation = next_observation
        step += 1
    return trace


def run_determinism(
    configs: Sequence[EpisodeConfig],
    count: int = 60,
) -> dict[str, Any]:
    if count > len(configs):
        raise ValueError("确定性场数不能超过唯一配置数")
    buckets = {
        encounter: [config for config in configs if config.encounter == encounter]
        for encounter in Encounter
    }
    selected: list[EpisodeConfig] = []
    base, remainder = divmod(count, len(Encounter))
    for index, encounter in enumerate(Encounter):
        take = base + (1 if index < remainder else 0)
        selected.extend(buckets[encounter][:take])
    if len(selected) != count:
        raise ValueError("配置集无法为确定性测试提供要求的三遭遇覆盖")
    failures: list[str] = []
    cross_path_failures: list[str] = []
    for config in selected:
        traces: dict[str, list[dict[str, Any]]] = {}
        for path_name in PATH_NAMES:
            first = replay_trace(path_name, config)
            second = replay_trace(path_name, config)
            if first != second:
                failures.append(f"{path_name}:config={config.index}")
            traces[path_name] = first
        baseline = traces[PATH_NAMES[0]]
        comparable_keys = (
            "step",
            "semantic_observation_sha256",
            "action_mask_hex",
            "action",
            "next_semantic_observation_sha256",
            "next_action_mask_hex",
            "reward_hex",
            "terminated",
            "truncated",
            "info",
        )
        baseline_semantic = [
            {key: row[key] for key in comparable_keys} for row in baseline
        ]
        for path_name in PATH_NAMES[1:]:
            candidate = [
                {key: row[key] for key in comparable_keys}
                for row in traces[path_name]
            ]
            if candidate != baseline_semantic:
                cross_path_failures.append(f"{path_name}:config={config.index}")
    return {
        "serialization_version": SERIALIZATION_VERSION,
        "episodes": len(selected),
        "encounter_counts": {
            encounter.value: sum(config.encounter == encounter for config in selected)
            for encounter in Encounter
        },
        "runs_per_path_episode": 2,
        "within_path_failures": failures,
        "cross_path_semantic_failures": cross_path_failures,
        "passed": not failures and not cross_path_failures,
    }


def _command_output(args: Sequence[str]) -> str:
    try:
        return subprocess.run(
            args,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"不可用：{exc}"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata(configs: Sequence[EpisodeConfig], patch_path: Path | None) -> dict[str, Any]:
    backend = _load_backend()
    extension = Path(backend.__file__).resolve()
    eval_seeds = ROOT / "eval_seeds.json"
    cache = ROOT / "third_party" / "sts_lightspeed" / "build" / "CMakeCache.txt"
    adapter_patch = ROOT / "patches" / "lightspeed-battle-env.patch"
    status = _command_output(("git", "status", "--short", "--branch"))
    return {
        "timestamp_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_commit": _command_output(("git", "rev-parse", "HEAD")),
        "git_status": status,
        "eval_seeds_sha256": _file_sha256(eval_seeds),
        "input_contract": {
            "schema_version": SCHEMA_VERSION,
            "registry_version": DEFAULT_CARD_REGISTRY.version,
            "registry_hash": DEFAULT_CARD_REGISTRY.content_hash,
            "serialization_version": SERIALIZATION_VERSION,
        },
        "worktree_patch": (
            {
                "path": str(patch_path.resolve()),
                "sha256": _file_sha256(patch_path),
            }
            if patch_path is not None and patch_path.is_file()
            else None
        ),
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "logical_cpu_count": os.cpu_count(),
            "python_executable": sys.executable,
            "python": sys.version,
            "numpy": np.__version__,
        },
        "build": {
            "extension_path": str(extension),
            "extension_sha256": _file_sha256(extension),
            "extension_size_bytes": extension.stat().st_size,
            "cmake": _command_output(
                (str(TOOLCHAIN / "cmake.exe"), "--version")
            ).splitlines()[0],
            "compiler": _command_output(
                (str(TOOLCHAIN / "g++.exe"), "--version")
            ).splitlines()[0],
            "ninja": _command_output((str(TOOLCHAIN / "ninja.exe"), "--version")),
            "cmake_cache_sha256": _file_sha256(cache) if cache.is_file() else None,
            "adapter_patch_sha256": (
                _file_sha256(adapter_patch) if adapter_patch.is_file() else None
            ),
            "upstream_commit": _command_output(
                ("git", "-C", str(ROOT / "third_party" / "sts_lightspeed"), "rev-parse", "HEAD")
            ),
            "upstream_status": _command_output(
                ("git", "-C", str(ROOT / "third_party" / "sts_lightspeed"), "status", "--short")
            ),
            "lightspeed_lock": json.loads(
                (ROOT / "scripts" / "lightspeed-lock.json").read_text(encoding="utf-8")
            ),
        },
        "thread_limits": {
            name: os.environ[name]
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
        "configuration": {
            "unique_configs": len(configs),
            "path_episodes_per_repeat": len(configs),
            "total_path_episodes_per_repeat": len(configs) * len(PATH_NAMES),
            "seed_start": configs[0].seed,
            "seed_end_inclusive": configs[-1].seed,
            "agent_seed_start": configs[0].agent_seed,
            "agent_seed_end_inclusive": configs[-1].agent_seed,
            "ascension": 0,
            "max_turns": 50,
            "gamma": 1.0,
            "encounter_counts": {
                encounter.value: sum(c.encounter == encounter for c in configs)
                for encounter in Encounter
            },
            "agent": "MaskedRandomAgent；每局独立 seed；全零 logits 经 masked_softmax 后在 Agent 内抽样",
            "timing_boundary": (
                "计入每局 reset、原始/规范/wrapper 观测转换、Agent 31 维 masked "
                "softmax 与抽样、decision 校验、runner 控制流、env.step 和统计记账；"
                "不计进程启动、预热、逐步序列化、输出写盘"
            ),
        },
    }


def acceptance_passed(report: Mapping[str, Any]) -> bool:
    if not report["determinism"]["passed"]:
        return False
    for path_name in PATH_NAMES:
        repetitions = report["performance"][path_name]["repetitions"]
        for run in repetitions:
            total = run["total"]
            if (
                total["episodes"] != report["metadata"]["configuration"]["unique_configs"]
                or total["exceptions"]
                or total["illegal_actions"]
                or total["hard_timeouts"]
                or not total["reward_contract_ok"]
            ):
                return False
        if report["performance"][path_name]["median_steps_per_second"] < 2000.0:
            return False
    return True


def run_acceptance(
    configs: Sequence[EpisodeConfig],
    repeats: int,
    warmup_episodes: int,
    determinism_episodes: int,
    patch_path: Path | None,
) -> dict[str, Any]:
    if repeats < 3:
        raise ValueError("正式性能验收至少重复 3 次")
    warmup = list(configs[:warmup_episodes])
    for path_name in PATH_NAMES:
        run_path(path_name, warmup)

    performance: dict[str, Any] = {}
    for path_name in PATH_NAMES:
        repetitions = [run_path(path_name, configs).report() for _ in range(repeats)]
        performance[path_name] = {
            "repetitions": repetitions,
            "median_steps_per_second": statistics.median(
                item["total"]["steps_per_second"] for item in repetitions
            ),
            "median_elapsed_seconds": statistics.median(
                item["total"]["elapsed_seconds"] for item in repetitions
            ),
            "by_encounter_medians": {
                encounter.value: {
                    "elapsed_seconds": statistics.median(
                        item["by_encounter"][encounter.value]["elapsed_seconds"]
                        for item in repetitions
                    ),
                    "steps_per_second": statistics.median(
                        item["by_encounter"][encounter.value]["steps_per_second"]
                        for item in repetitions
                    ),
                }
                for encounter in Encounter
            },
        }
    report: dict[str, Any] = {
        "metadata": metadata(configs, patch_path),
        "warmup_episodes_per_path": len(warmup),
        "performance_repeats": repeats,
        "determinism": run_determinism(configs, determinism_episodes),
        "performance": performance,
    }
    report["passed"] = acceptance_passed(report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=10_000)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmup-episodes", type=int, default=100)
    parser.add_argument("--determinism-episodes", type=int, default=60)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "build" / "week4-t5-acceptance.json",
    )
    parser.add_argument("--worktree-patch", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    configs = build_configs(args.episodes)
    report = run_acceptance(
        configs=configs,
        repeats=args.repeats,
        warmup_episodes=args.warmup_episodes,
        determinism_episodes=args.determinism_episodes,
        patch_path=args.worktree_patch,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output.resolve()),
        "passed": report["passed"],
        "median_steps_per_second": {
            name: report["performance"][name]["median_steps_per_second"]
            for name in PATH_NAMES
        },
    }, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
