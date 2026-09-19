"""Transitive leakage and tamper checks independent of model scores."""
import importlib.util
import json
from pathlib import Path
import pytest
from initial_state import read_records

PROJECT = Path(__file__).resolve().parent


def load(name):
    spec=importlib.util.spec_from_file_location(name,PROJECT/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_transitive_overlap_is_one_component():
    connect=load('reconstruct-pilot').connect
    rows=[{'state_hash':s,'provenance':{'source_group':g}}
          for g,s in [('a','x'),('b','x'),('b','y'),('c','y'),('d','z')]]
    result=connect(rows)
    assert result['a']==result['b']==result['c']
    assert result['d']['component']!=result['a']['component']
    assert connect(list(reversed(rows)))==result


def test_produced_corpus_has_no_source_or_state_leakage():
    rows=read_records(PROJECT/'pilot-states.jsonl')
    assert len({r['state_hash'] for r in rows})==len(rows)
    assignments={}
    for row in rows:
        p=row['provenance']
        for origin in p['origins']:
            key=origin['source_group']; assigned=(p['component'],p['partition'])
            assert assignments.setdefault(key,assigned)==assigned
            assert origin['component']==p['component']
            assert origin['partition']==p['partition']
        assert row['training_admitted'] is False
        assert row['evidence']['historical_rules_equivalence']=='unverified'


def test_corrupt_archive_rejected_before_inventory(tmp_path):
    module=load('inventory-source'); path=tmp_path/'bad.zip';path.write_bytes(b'bad')
    with pytest.raises(ValueError): module.build_inventory(path,tmp_path)


def test_all_source_combats_have_exactly_one_ledger_row():
    inventory=json.loads((PROJECT/'source-inventory.json').read_text())
    ledger=[json.loads(line) for line in (PROJECT/'candidate-ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(ledger)==inventory['counts']['combat_records']
    assert len({r['scene_id'] for r in ledger})==len(ledger)
    assert all((r['state_hash'] is not None) != bool(r['blockers']) for r in ledger)
