"""Guardrails for the standalone frozen-policy diagnostic."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('replay', ROOT/'scripts/replay-m0-dev.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


def test_dev_only_and_original_seed():
    corpus = SimpleNamespace(rows={'x': {'provenance': {'partition': 'audit-dev'}}})
    case = dict(state_hash='x', environment_seed=0, policy_seed=700000)
    replay.require_dev(case, corpus)
    with pytest.raises(ValueError):
        replay.require_dev({**case, 'environment_seed': 1}, corpus)
    corpus.rows['x']['provenance']['partition'] = 'audit-holdout'
    with pytest.raises(ValueError):
        replay.require_dev(case, corpus)


def test_end_turn_flag_is_only_a_candidate_not_a_verdict():
    end = dict(task='END_TURN', joint_probability=.9)
    assert replay.suspicion(end, [end]) == []
    assert replay.suspicion(end, [end, dict(task='PLAY')]) == ['end-turn-with-legal-alternative']


def test_reproduction_requires_outcome_and_return():
    row = dict(steps=3, win=0, potion_uses=1, terminated=True, truncated=False,
               reward=-.5, exit_hp_ratio=0.)
    replay.assert_reproduced(row, row)
    with pytest.raises(ValueError):
        replay.assert_reproduced({**row, 'reward': -.4}, row)


@pytest.mark.skipif(not (ROOT/'runs/a-v2-ppo-v1/dev-0256-episodes.jsonl').exists(),
                    reason='Local frozen run artifacts are required')
def test_selection_is_bounded_and_paired():
    selection, final = replay.select_cases(ROOT/'runs/a-v2-ppo-v1',
        ROOT/'projects/battle-initial-states/corpora/a-v2')
    assert 1 <= len(selection) <= 30
    assert set(selection) <= set(final)
    assert any('winning-parent' in reasons for reasons in selection.values())


def test_no_training_dependency_or_update():
    source = (ROOT/'scripts/replay-m0-dev.py').read_text(encoding='utf-8')
    for forbidden in ('from sts.train', 'torch.optim', '.backward(', 'torch.save('):
        assert forbidden not in source


def test_numpy_observation_serialization(tmp_path):
    import numpy as np
    path = tmp_path/'observation.json'
    replay.write(path, {'mask': np.array([True, False]), 'value': np.int64(2)})
    assert replay.read(path) == {'mask': [True, False], 'value': 2}
