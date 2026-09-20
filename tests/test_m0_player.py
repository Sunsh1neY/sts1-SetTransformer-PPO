"""Offline player transformations and source fidelity."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('player_builder', ROOT/'scripts/build-m0-player.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_action_labels_preserve_target_slots_and_selection():
    obs={'hand':[{'name':'Strike_R','upgrade_count':1,'target_kind':'ENEMY'}],
         'enemies':[{'name':'A'},{'name':'B'}],
         'potions':[{'name':'FirePotion','target_kind':'ENEMY'}],
         'decision':{'selection':{'candidates':[{'name':'Headbutt'}]}}}
    def normal(action):return {'route':{'kind':'NORMAL','action':action}}
    assert builder.action_label(normal(1),obs)=='Strike_R+ → B [2]'
    assert builder.action_label(normal(52),obs)=='FirePotion → B [2]'
    assert builder.action_label(normal(50),obs)=='END TURN'
    assert builder.action_label({'task':'EXHUME','route':{'kind':'SELECT_CARD','candidate_index':0}},obs)=='EXHUME: Headbutt'


@pytest.mark.skipif(not (ROOT/'runs/m0-player-traces-v1/summary.json').exists(),reason='Local replay artifacts')
def test_all_recorded_branches_and_terminal_frames(tmp_path):
    directory=ROOT/'runs/m0-player-traces-v1'
    output=tmp_path/'index.html'
    builder.build(directory,output)
    html=output.read_text(encoding='utf-8')
    payload=html.split('<script id="replay-data" type="application/json">',1)[1].split('</script>',1)[0]
    data=json.loads(payload)
    assert len(data['cases'])==3
    assert sum(len(c['branches']) for c in data['cases'])==5
    for case in data['cases']:
        for trace in [case['original']]+case['branches']:
            assert len(trace['frames'])==trace['result']['steps']+1
            assert trace['frames'][-1]['terminal'] and trace['frames'][-1]['value'] is None
        for branch in case['branches']:
            i=branch['at']-1
            assert branch['frames'][i]['state']==case['original']['frames'][i]['state']
            assert sum(f['forced'] for f in branch['frames'])==1
            assert branch['frames'][i]['chosen']['route']!=case['original']['frames'][i]['chosen']['route']
    assert '<script src=' not in html and 'fetch(' not in html
    with pytest.raises(ValueError,match='overwrite'):
        builder.build(directory,output)


def test_incomplete_runs_are_rejected(tmp_path):
    (tmp_path/'summary.json').write_text('{"status":"incomplete"}',encoding='utf-8')
    with pytest.raises(ValueError,match='completed'):
        builder.build(tmp_path,tmp_path/'out.html')
