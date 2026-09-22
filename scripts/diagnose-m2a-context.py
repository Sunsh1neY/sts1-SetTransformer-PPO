"""Frozen selected-M2a dev intervention and historical runtime diagnostics.

No optimizer, backward, checkpoint writes, holdout access or training extension.
Whole-policy delta-off is a dependency intervention, not retrained M0.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from collections import Counter

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read(path):
    return json.loads(path.read_bytes())


def rows(path):
    return [json.loads(x) for x in path.read_bytes().splitlines()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf8')


def append(path, value):
    with path.open('a', encoding='utf8') as f:
        f.write(json.dumps(value, allow_nan=False)+'\n')


def runtime_analysis():
    import numpy as np
    result = {}
    for name in ('a-v2-ppo-v1', 'm2a-source-context-v1'):
        records = rows(ROOT/'runs'/name/'metrics.jsonl')
        features = []
        for r in records:
            groups = r['groups'].values()
            total = sum(g['transitions'] for g in groups)
            features.append(dict(update=r['iteration'], collect=r['collect_seconds'],
                optimize=r['update_seconds'],
                entities=sum(g['entities']*g['transitions'] for g in groups)/total,
                legal_actions=sum(g['legal_actions']*g['transitions'] for g in groups)/total,
                augmentation_fraction=r['groups'].get('augmentation', {}).get('transitions', 0)/total))
        windows = []
        for start in range(0, len(features), 32):
            subset = features[start:start+32]
            windows.append(dict(first=subset[0]['update'], last=subset[-1]['update'],
                **{k:float(np.mean([r[k] for r in subset])) for k in features[0] if k!='update'}))
        correlations = {f'{x}_vs_{y}':float(np.corrcoef([r[x] for r in features], [r[y] for r in features])[0, 1])
            for x in ('collect', 'optimize') for y in ('entities', 'legal_actions', 'augmentation_fraction')}
        changes = sorted([dict(update=b['update'], ratio=(b['collect']+b['optimize'])/(a['collect']+a['optimize']),
            before=a, after=b) for a, b in zip(features, features[1:])], key=lambda r:abs(__import__('math').log(r['ratio'])), reverse=True)[:8]
        result[name] = dict(windows=windows, correlations=correlations, largest_adjacent_changes=changes,
            collect_update_correlation=float(np.corrcoef([r['collect'] for r in features], [r['optimize'] for r in features])[0, 1]),
            rows=features)
    result['limits'] = ['Means do not capture padded maximum token lengths or attention microbatch splits.',
        'Historical power, clock, thermal and competing-process telemetry was not recorded.',
        'Correlation and adjacent workload matching cannot establish hardware root cause.']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT/'third_party/sts_lightspeed/build'))
    import numpy as np
    import torch
    from sts.env.acorpus import ACorpus
    from sts.env.lightspeed import _load_backend
    from sts.models.apath import TASKS, JointDistribution
    from sts.models.architectures.m2a_source_context.model import M2aActorCritic
    from sts.train.corpus_evaluation import evaluate, summarize, strata, paired_comparison

    out = args.output.resolve()
    frozen = (ROOT/'runs/m2a-source-context-v1').resolve()
    if out == frozen or frozen in out.parents:
        raise ValueError('Output must be outside the frozen run')
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    deadline = started + 1800
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    corpus_path = ROOT/'projects/battle-initial-states/corpora/a-v2'
    fp = read(frozen/'fingerprint.json')

    def verify():
        for name, expected in fp.items():
            path = Path(_load_backend().__file__) if name=='backend' else corpus_path/name[7:] if name.startswith('corpus/') else ROOT/name
            if sha(path) != expected:
                raise ValueError('Frozen fingerprint mismatch: '+name)

    verify()
    checkpoint_path = frozen/'selected.pt'
    checkpoint_hash = sha(checkpoint_path)
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    if checkpoint['fingerprint'] != fp or checkpoint['model_version'] != M2aActorCritic.model_version or checkpoint['iteration'] != 192:
        raise ValueError('Selected checkpoint identity mismatch')
    model = M2aActorCritic().cuda().eval().requires_grad_(False)
    model.load_state_dict(checkpoint['model'], strict=True)
    original = {k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
    corpus = ACorpus(corpus_path)
    cases = read(frozen/'evaluation-cases.json')['audit-dev']
    if len(cases)!=288 or len({r['state_hash'] for r in cases})!=288:
        raise ValueError('Unexpected dev population')
    for case in cases:
        if corpus.rows[case['state_hash']]['provenance']['partition']!='audit-dev' or case['environment_seed']!=0 or case['policy_seed']!=700000:
            raise ValueError('Invalid dev case')
    historical = {r['state_hash']:r for r in rows(frozen/'dev-0192-episodes.jsonl')}
    write(out/'runtime.json', runtime_analysis())
    write(out/'manifest.json', dict(checkpoint_sha256=checkpoint_hash, update=192, fingerprint=fp,
        script_sha256=sha(Path(__file__)), cases=cases, seconds_cap=1800,
        intervention='Zero output of source_query_delta via temporary forward hook; no parameter changes'))
    decisions = []

    class Policy(torch.nn.Module):
        def __init__(self, off=False):
            super().__init__()
            self.base = model
            self.off = off
            self.case_index = 0
            self.step = 0

        def forward(self, batch):
            self.step += 1
            if self.off:
                handle = model.source_query_delta.register_forward_hook(lambda module, inputs, output:torch.zeros_like(output))
                try:
                    return model(batch)
                finally:
                    handle.remove()
            h, critic = model.encode_entities(batch)
            captured = {}
            def capture(module, inputs, output):
                captured['delta_norm'] = float(output.norm(dim=-1).mean())
            handle = model.source_query_delta.register_forward_hook(capture)
            try:
                sl, tl = model.readout_logits(h, batch)
            finally:
                handle.remove()
            handle = model.source_query_delta.register_forward_hook(lambda module, inputs, output:torch.zeros_like(output))
            try:
                sl_off, tl_off = model.readout_logits(h, batch)
            finally:
                handle.remove()
            end = (batch['task']==TASKS.index('END_TURN')) & batch['source_mask']
            if not torch.equal(sl[end], sl_off[end]) or not torch.equal(tl, tl_off):
                raise ValueError('Intervention leaked into raw END_TURN or target head')
            normal = JointDistribution(sl, tl, batch['source_mask'], batch['target_mask'])
            off = JointDistribution(sl_off, tl_off, batch['source_mask'], batch['target_mask'])
            p, q = normal.probs, off.probs
            row = dict(state_hash=cases[self.case_index]['state_hash'], step=self.step,
                joint_map_changed=bool(p.flatten().argmax()!=q.flatten().argmax()),
                source_map_changed=bool(normal.source_probs.argmax()!=off.source_probs.argmax()),
                total_variation=float((p-q).abs().sum()/2),
                endturn_probability=float(normal.source_probs[end].sum()),
                endturn_probability_off=float(off.source_probs[end].sum()), **captured)
            decisions.append(row)
            append(out/'same-state-decisions.jsonl', row)
            return normal, model.value_head(critic).squeeze(-1)

    def run(off):
        policy = Policy(off)
        label = 'delta-off' if off else 'normal'
        def on_case(row, done, total):
            if not off:
                old = historical[row['state_hash']]
                for k in ('win', 'steps', 'terminated', 'truncated', 'potion_uses'):
                    if row[k]!=old[k]:
                        raise ValueError('Historical reproduction mismatch: '+k)
                for k in ('reward', 'exit_hp_ratio'):
                    if abs(row[k]-old[k])>1e-9:
                        raise ValueError('Historical reproduction mismatch: '+k)
            append(out/(label+'-episodes.jsonl'), row)
            policy.case_index = done
            policy.step = 0
            if done%16==0 or done==total:
                status = dict(phase=label, completed=done, total=total, elapsed=time.monotonic()-started)
                write(out/'status.json', status)
                print(json.dumps(status), flush=True)
        return evaluate(policy, corpus, cases, deadline, on_case)

    try:
        normal, off = run(False), run(True)
        differences = paired_comparison(normal, off)
        switches = Counter((a['win'], b['win']) for a,b in zip(normal, off))
        per_state = {}
        for case in cases:
            subset = [r for r in decisions if r['state_hash']==case['state_hash']]
            per_state[case['state_hash']] = dict(mean_tv=float(np.mean([r['total_variation'] for r in subset])),
                changed_fraction=float(np.mean([r['joint_map_changed'] for r in subset])))
        result = dict(normal=summarize(normal), delta_off=summarize(off), normal_strata=strata(normal),
            delta_off_strata=strata(off), paired= differences,
            win_transitions={f'{a}->{b}':n for (a,b),n in switches.items()},
            decision_count=len(decisions), joint_map_changed=sum(r['joint_map_changed'] for r in decisions),
            mean_decision_tv=float(np.mean([r['total_variation'] for r in decisions])),
            mean_state_tv=float(np.mean([v['mean_tv'] for v in per_state.values()])), per_state=per_state,
            raw_head_isolation_verified=True, historical_cases_reproduced=288,
            note='Single policy seed; later trajectories/RNG consumption diverge. Delta-off is not M0 or a retrained ablation.')
        write(out/'results.json', result)
        write(out/'status.json', dict(phase='complete', elapsed=time.monotonic()-started))
    except Exception as exc:
        write(out/'status.json', dict(phase='failed', error=repr(exc), elapsed=time.monotonic()-started))
        raise
    finally:
        verify()
        if sha(checkpoint_path)!=checkpoint_hash or any(not torch.equal(original[k],v.cpu()) for k,v in model.state_dict().items()):
            raise ValueError('Frozen weights changed')
        write(out/'integrity.json', dict(checkpoint_unchanged=True, model_tensors_unchanged=True, fingerprint_unchanged=True))


if __name__=='__main__':
    main()
