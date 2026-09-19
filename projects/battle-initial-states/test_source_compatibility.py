"""Protect source-certification boundaries and floor-band accounting."""
import importlib.util
import json
from pathlib import Path
import pytest
from source_fields import scene_key

PROJECT=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('source_audit',PROJECT/'audit-source-compatibility.py')
AUDIT=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(AUDIT)


@pytest.mark.parametrize('floor,expected',[(1,'act1'),(17,'act1'),(18,'act2'),(34,'act2'),(35,'act3'),(51,'act3'),(52,'act4_or_later'),(1.0,'act1'),(18.0,'act2')])
def test_floor_boundaries(floor,expected):
    assert AUDIT.band(floor)==expected


@pytest.mark.parametrize('value',[True,False,0,-1,1.5,float('nan'),float('inf'),'1'])
def test_lossy_or_ambiguous_floors_rejected(value):
    with pytest.raises(ValueError): AUDIT.band(value)


def test_integral_float_scene_join_regression():
    status={scene_key('source',1,0):'reconstructed'}
    assert status[scene_key('source',1.0,0)]=='reconstructed'
    assert scene_key('source',2,0)!=scene_key('source',1,0)
    assert scene_key('source',1,1)!=scene_key('source',1,0)


@pytest.mark.parametrize('run',[{}, {'build_version':'2022-12-18'},
                              {'basemod:card_modifiers':[None,None]},
                              {'is_prod':False,'mods':['RunHistoryPlus']}])
def test_metadata_is_not_certification(run):
    assert AUDIT.classify(run)['status']=='unverified'


def test_explicit_nonstandard_mode_is_a_separate_scope_mismatch():
    assert AUDIT.classify({'is_daily':True})['status']=='declared_mode_outside_pilot'


def test_all_groups_and_combats_accounted_for():
    report=json.loads((PROJECT/'source-compatibility.json').read_text(encoding='utf-8'))
    counts=report['counts']
    assert sum(counts['combat_by_floor_band'].values())==counts['combats']
    assert sum(m['groups'] for m in report['source_build_matrix'])==counts['source_groups']
    assert len({g['source_group'] for g in report['groups']})==counts['source_groups']
    assert report['entry_vs_final_deck_example']['different_multisets']
    assert report['newly_certified_A_states']==0
