"""S3正式C++采样、原mask更新和精确恢复的整合回归。"""

import json
import hashlib
import zipfile
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import torch

from sts.models.overfit import weight_hash
from sts.train.ppo import PPOConfig, PPOTrainer, compute_gae
from sts.train.recording import record_failure, record_metadata, validate_resume_origin


@pytest.fixture(autouse=True)
def single_thread():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def config(**kwargs):
    return replace(PPOConfig(), total_timesteps=384, num_envs=3, num_steps=32, num_minibatches=3, update_epochs=2, **kwargs)


def test_真实rollout用原mask复算旧logprob且快照不变():
    trainer = PPOTrainer(config())
    rollout = trainer.collector.collect(trainer.agent)
    batch = {key: value.flatten(0, 1) for key, value in rollout.observations.items()}
    actions = rollout.actions.flatten()
    _, logprob, _, values, _ = trainer.model.action_and_value(batch, actions)
    torch.testing.assert_close(logprob, rollout.logprobs.flatten())
    torch.testing.assert_close(values, rollout.values.flatten())
    assert batch["action_mask"].gather(1, actions[:, None]).all()
    assert rollout.terminated.any()
    assert not rollout.truncated.any()
    assert torch.equal(rollout.episode_ends, rollout.terminated)
    assert any(not np.array_equal(left.numpy(), right.numpy()) for left, right in zip(rollout.observations["action_mask"][:-1], rollout.observations["action_mask"][1:]))
    original = {key: value.clone() for key, value in rollout.observations.items()}
    trainer.collector.collect(trainer.agent)
    assert all(torch.equal(original[key], value) for key, value in rollout.observations.items())


def test_任务硬超时是失败且不自举():
    trainer = PPOTrainer(config(max_turns=1))
    rollout = trainer.collector.collect(trainer.agent)
    assert rollout.episodes and any(episode["timeout"] for episode in rollout.episodes)
    assert all(episode["total_reward"] == 0 for episode in rollout.episodes if episode["timeout"])
    advantages, returns = compute_gae(rollout.rewards, rollout.values, torch.full_like(rollout.next_values, 9999), rollout.terminated)
    assert torch.equal(returns[rollout.terminated], rollout.rewards[rollout.terminated])
    assert torch.isfinite(advantages).all()


def test_训练更新及断点恢复下一批和权重逐字节一致(tmp_path):
    uninterrupted = PPOTrainer(config())
    initial = weight_hash(uninterrupted.model)
    first, episodes = uninterrupted.train_iteration()
    assert initial != weight_hash(uninterrupted.model)
    assert episodes and first["illegal_actions"] == 0
    assert first["global_step"] == 96
    path = tmp_path / "checkpoint.pt"
    uninterrupted.save(path)
    expected_metrics, expected_episodes = uninterrupted.train_iteration()
    restored = PPOTrainer.load(path)
    actual_metrics, actual_episodes = restored.train_iteration()
    assert actual_metrics == expected_metrics
    assert actual_episodes == expected_episodes
    assert weight_hash(restored.model) == weight_hash(uninterrupted.model)
    assert torch.equal(restored.agent.rng.get_state(), uninterrupted.agent.rng.get_state())
    assert restored.shuffle_rng.bit_generator.state == uninterrupted.shuffle_rng.bit_generator.state
    assert restored.collector.state_dict() == uninterrupted.collector.state_dict()


@pytest.mark.parametrize("field,value", [("backend_sha256", "wrong"), ("iteration", 9999)])
def test_恢复拒绝后端或进度漂移(tmp_path, field, value):
    trainer = PPOTrainer(config())
    path = tmp_path / "checkpoint.pt"
    trainer.save(path)
    payload = torch.load(path, weights_only=True)
    payload["extra"][field] = value
    torch.save(payload, path)
    with pytest.raises(ValueError):
        PPOTrainer.load(path)


def test_恢复拒绝任务或奖励版本漂移(tmp_path):
    trainer = PPOTrainer(config())
    path = tmp_path / "checkpoint.pt"
    trainer.save(path)
    payload = torch.load(path, weights_only=True)
    payload["extra"]["reward_contract"]["reward_version"] = "run_reward_v1"
    torch.save(payload, path)
    with pytest.raises(ValueError):
        PPOTrainer.load(path)


@pytest.mark.parametrize("kwargs", [
    {"gamma": 0.99}, {"total_timesteps": 100}, {"num_minibatches": 1024},
    {"ent_coef": float("nan")}, {"vf_coef": float("inf")},
    {"train_seed_start": 900000}, {"model_seed": 0}, {"target_kl": -1},
])
def test_拒绝错误预算奖励或seed配置(kwargs):
    with pytest.raises(ValueError):
        PPOConfig(**kwargs)


def test_cli恢复核对python源码清单(tmp_path):
    metadata = record_metadata(tmp_path)
    root = Path(__file__).resolve().parents[1]
    with zipfile.ZipFile(tmp_path / "source.zip") as archive:
        for name in ("spec-v6.md", "archive/spec-v4.md", "archive/spec-v5.md"):
            assert archive.read(name) == (root / name).read_bytes()
            assert hashlib.sha256(archive.read(name)).hexdigest() == metadata["source_manifest"][name]
        assert "spec-v4.md" not in archive.namelist()
        assert "spec-v5.md" not in archive.namelist()
    trainer = PPOTrainer(config())
    path = tmp_path / "checkpoint-0000.pt"
    trainer.save(path, metadata={"source_archive_sha256": metadata["source_archive_sha256"]})
    assert validate_resume_origin(path)["source_manifest"] == metadata["source_manifest"]
    metadata["source_manifest"]["sts/train/ppo.py"] = "0" * 64
    (tmp_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="训练代码与原run不一致"):
        validate_resume_origin(path)


def test_失败记录只指向已有完整快照(tmp_path):
    (tmp_path / "metrics.jsonl").write_text('{"iteration": 3}\n', encoding="utf-8")
    path = tmp_path / "checkpoint-0002.pt"
    path.write_bytes(b"existing checkpoint")
    record_failure(tmp_path, FloatingPointError("非有限梯度"), "training")
    report = json.loads((tmp_path / "failure.json").read_text(encoding="utf-8"))
    assert report["status"] == "failed" and not report["training_completed"]
    assert report["last_logged_iteration"] == 3
    assert report["last_complete_checkpoint"] == "checkpoint-0002.pt"
    assert report["error_type"] == "FloatingPointError"
    assert path.read_bytes() == b"existing checkpoint"
