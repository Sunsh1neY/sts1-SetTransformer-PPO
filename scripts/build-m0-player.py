"""Build a dependency-free, offline battle replay player from verified traces."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_bytes())


def action_label(candidate, obs):
    route = candidate['route']
    if route['kind'] != 'NORMAL':
        index = route['candidate_index']
        cards = obs['decision']['selection']['candidates']
        return candidate['task']+': '+cards[index]['name']
    action = route['action']
    if action == 50:
        return 'END TURN'
    if action < 50:
        card = obs['hand'][action//5]
        label = card['name']+('+' if card['upgrade_count'] else '')
    else:
        card = obs['potions'][(action-51)//5]
        label = card['name']
    if card['target_kind'] == 'ENEMY':
        slot = action % 5 if action < 50 else (action-51) % 5
        label += ' → '+obs['enemies'][slot]['name']+f' [{slot+1}]'
    return label


def pack_trace(trace):
    result = trace['result']
    frames = []
    def frame(obs):
        return {key: obs.get(key) for key in ('player','enemies','hand','potions','relics',
                'draw_pile','discard_pile','exhaust_pile','decision')}
    for step in trace['steps']:
        obs = step['observation']
        candidates = [{**c, 'label': action_label(c, obs)} for c in step['candidates']]
        frames.append(dict(state=frame(obs), step=step['step'], value=step['value'],
            candidates=candidates, chosen={**step['chosen'], 'label':action_label(step['chosen'],obs)},
            forced=step.get('forced',False), terminal=False, flags=step['flags']))
    terminal = trace['steps'][-1].get('terminal_observation')
    if terminal is None:
        raise ValueError('A true terminal observation is required; do not invent it')
    frames.append(dict(state=frame(terminal), step=result['steps']+1, value=None,
                       candidates=[], chosen=None, forced=False, terminal=True, flags=[]))
    return dict(result=result, frames=frames)


def build(directory, output):
    summary = read(directory/'summary.json')
    if summary['status'] != 'complete' or not summary['weights_unchanged'] or not summary['dependencies_unchanged']:
        raise ValueError('Only completed, fingerprint-verified replay artifacts are supported')
    manifest = read(directory/'manifest.json')
    probes = read(directory/'probes.json')
    cases = []
    for key in dict.fromkeys(p['state_hash'] for p in probes):
        original = pack_trace(read(directory/(key+'.json')))
        branches = []
        for p in probes:
            if p['state_hash'] != key:
                continue
            path = (directory/p['trace_file']).resolve()
            if path.parent != directory.resolve():
                raise ValueError('Trace path escapes input directory')
            branch = pack_trace(read(path))
            branch.update(at=p['step'], label=action_label(p['alternative'],read(directory/(key+'.json'))['steps'][p['step']-1]['observation']))
            branches.append(branch)
        enemies = original['frames'][0]['state']['enemies']
        cases.append(dict(id=key, title=' / '.join(e['name'] for e in enemies if e['present']),
                          original=original, branches=branches))
    data = dict(cases=cases, checkpoint=manifest['checkpoint_sha256'],
                environment_seed=0, policy_seed=700000, model='M0 · update 256',
                source=directory.name, schema='m0-battle-player-v1')
    template = (ROOT/'projects/battle-initial-states/player/player.html').read_text(encoding='utf-8')
    payload = json.dumps(data, ensure_ascii=False, separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    if output.exists():
        raise ValueError('Refusing to overwrite player output')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(template.replace('__REPLAY_DATA__', payload),encoding='utf-8')
    print(json.dumps(dict(output=str(output),cases=len(cases),branches=len(probes),
                    bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest())))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--traces',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.traces,args.output)
