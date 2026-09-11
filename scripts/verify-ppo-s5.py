"""只读原始S4产物，在新目录验证实际checkpoint恢复和开发评估复现。"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
import yaml

from sts.eval import evaluate_diagnostic
from sts.models.overfit import weight_hash
from sts.train.ppo import PPOTrainer
from sts.train.recording import validate_resume_origin


def same(left, right):
    """递归逐值比较权重、优化器、RNG和环境恢复状态。"""
    if isinstance(left, torch.Tensor):
        return isinstance(right, torch.Tensor) and torch.equal(left, right)
    if isinstance(left, np.ndarray):
        return np.array_equal(left, right)
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    results = []
    for group in 'abc':
        directory = root / 'runs' / f'ppo-s4-{group}-20260911'
        checkpoint = directory / 'checkpoint-0224.pt'
        metadata = validate_resume_origin(checkpoint)
        metrics = [json.loads(line) for line in (directory / 'metrics.jsonl').read_text(encoding='utf-8').splitlines()]
        report = json.loads((directory / 'report.json').read_text(encoding='utf-8'))
        trainer = PPOTrainer.load(checkpoint)
        replayed_episodes = []
        while trainer.iteration < 256:
            actual, episodes = trainer.train_iteration()
            expected = {k: v for k, v in metrics[trainer.iteration - 1].items() if k != 'steps_per_second'}
            assert actual == expected, (group, trainer.iteration, '指标不一致')
            replayed_episodes.extend(episodes)
        original_episodes = [json.loads(line) for line in (directory / 'episodes.jsonl').read_text(encoding='utf-8').splitlines()]
        assert replayed_episodes == original_episodes[-len(replayed_episodes):], '恢复轨迹不一致'
        final_path = directory / 'checkpoint-0256.pt'
        original = torch.load(final_path, weights_only=True, map_location='cpu')
        restored_path = args.output / f'{group}-restored-0256.pt'
        trainer.save(restored_path, metadata=original['extra']['metadata'])
        restored = torch.load(restored_path, weights_only=True, map_location='cpu')
        assert same(original, restored), '最终checkpoint内容不一致'
        assert weight_hash(trainer.model) == report['final_weight_sha256']
        config = yaml.safe_load((directory / 'config.yaml').read_text(encoding='utf-8'))
        evaluation = evaluate_diagnostic(trainer.model, **config['diagnostic'])
        expected_evaluation = json.loads((directory / 'diagnostic-after.json').read_text(encoding='utf-8'))
        assert evaluation == expected_evaluation, '最终开发评估不一致'
        result = {
            'group': group, 'iterations_replayed': 32, 'episodes_replayed': len(replayed_episodes),
            'metrics_exact': True, 'episodes_exact': True, 'checkpoint_payload_exact': True,
            'evaluation_exact': True, 'final_weight_sha256': weight_hash(trainer.model),
            'checkpoint_file_sha256': hashlib.sha256(final_path.read_bytes()).hexdigest(),
            'source_archive_sha256': metadata['source_archive_sha256'],
        }
        results.append(result)
        (args.output / 'verification.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
