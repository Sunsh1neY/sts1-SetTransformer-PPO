"""Regression checks for immutable versions and synthetic lineage boundaries."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest
from initial_state import read_records

PROJECT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('version_corpora_tests', PROJECT/'version-corpora.py')
VERSIONS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERSIONS)


def test_baseline_is_exact_subset_and_partitions_are_inherited():
    baseline = {r['state_hash']:r for r in read_records(PROJECT/'corpora/a-v1/states.jsonl')}
    combined = {r['state_hash']:r for r in read_records(PROJECT/'corpora/a-v2/states.jsonl')}
    assert all(combined[k] == row for k,row in baseline.items())
    for row in read_records(PROJECT/'corpora/a-v2/additions.jsonl'):
        parent = baseline[row['evidence']['augmentation']['parent_state_hash']]
        assert row['source_backbone'] == parent['source_backbone']
        assert row['provenance']['partition'] == parent['provenance']['partition']
        assert row['provenance']['component'] == parent['provenance']['component']


def test_counter_variants_change_only_one_owned_registered_counter():
    baseline = {r['state_hash']:r for r in read_records(PROJECT/'corpora/a-v1/states.jsonl')}
    registry = {r['name']:r for r in json.loads((PROJECT.parents[1]/'sts/env/relic-state-registry.json').read_text())['relics']}
    for row in read_records(PROJECT/'corpora/a-v2/additions.jsonl'):
        aug = row['evidence']['augmentation']
        if aug['category'] != 'entry-counter':
            continue
        n, v = aug['parameters']['relic'], aug['parameters']['counter']
        expected = copy.deepcopy(baseline[aug['parent_state_hash']]['state'])
        relic = next(r for r in expected['relics'] if isinstance(r,dict) and r['name']==n)
        relic['counter'] = v
        assert registry[n]['counter']['min'] <= v <= registry[n]['counter']['max']
        assert row['state'] == expected


def test_frozen_file_tampering_is_rejected(tmp_path):
    (tmp_path/'data').write_bytes(b'original')
    VERSIONS.save(tmp_path/'manifest.json', {'files': {'data': {'sha256':VERSIONS.sha(tmp_path/'data')}}})
    VERSIONS.verify(tmp_path)
    (tmp_path/'data').write_bytes(b'changed')
    with pytest.raises(ValueError, match='Frozen artifact changed'):
        VERSIONS.verify(tmp_path)


def test_existing_v2_cannot_be_overwritten(monkeypatch):
    before = VERSIONS.sha(PROJECT/'corpora/a-v2/states.jsonl')
    with pytest.raises(ValueError, match='refusing to overwrite'):
        VERSIONS.build()
    assert VERSIONS.sha(PROJECT/'corpora/a-v2/states.jsonl') == before
