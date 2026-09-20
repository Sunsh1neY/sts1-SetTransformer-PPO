"""Read-only M0 dev replay and bounded single-action counterfactual probes.

No trainer import, optimizer, backward call, corpus mutation, or checkpoint save.
Counterfactuals are single-seed witnesses, not optimal-action labels.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read(path):
    return json.loads(Path(path).read_bytes())


def rows(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    def arrays(obj):
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.generic):
            return obj.item()
        raise TypeError('Unsupported diagnostic value: '+type(obj).__name__)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False, default=arrays)+'\n', encoding='utf-8')


def plain(route):
    return {k: v for k, v in route.items() if k not in ('snapshot', 'decision_id')}


def semantic_digest(sample):
    value = dict(tokens=[(t.entity_type, t.features.tolist()) for t in sample.entities.tokens],
        routes=[[plain(r) for r in rr] for rr in sample.routes],
        sources=sample.sources, targets=sample.targets, tasks=sample.tasks,
        held=sample.entities.held_card_index.tolist(), context=sample.context.tolist())
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def select_cases(run, corpus):
    history = [{r['state_hash']: r for r in rows(run/f'dev-{i:04d}-episodes.jsonl')}
               for i in (64, 128, 192, 256)]
    final = history[-1]
    selected = {}
    def add(key, reason):
        selected.setdefault(key, []).append(reason)
    # Two persistent failures per boss/component, not per generated variant.
    counts = {}
    for key, r in sorted(final.items()):
        bucket = (r['encounter'], r['component'])
        if r['encounter'] in ('CHAMP', 'THE_GUARDIAN') and all(h[key]['win'] == 0 for h in history):
            if counts.get(bucket, 0) < 2:
                add(key, 'persistent-boss'); counts[bucket] = counts.get(bucket, 0)+1
    # One losing low-HP child per winning parent, with its paired control.
    parents = set()
    for item in sorted(rows(corpus/'lineage.jsonl'), key=lambda x: x['state_hash']):
        child, parent = item['state_hash'], item['parent_state_hash']
        if (item['category'] == 'act2-low-hp' and child in final and parent in final
                and not final[child]['win'] and final[parent]['win'] and parent not in parents):
            add(child, 'low-hp-child'); add(parent, 'winning-parent'); parents.add(parent)
    for key, r in sorted(final.items()):
        if not r['win'] and any(h[key]['win'] for h in history[:-1]):
            add(key, 'checkpoint-sensitive')
            if sum('checkpoint-sensitive' in v for v in selected.values()) >= 3:
                break
    return selected, final


def require_dev(case, corpus):
    if corpus.rows[case['state_hash']]['provenance']['partition'] != 'audit-dev':
        raise ValueError('Only dev states are permitted')
    if case['environment_seed'] != 0 or case['policy_seed'] != 700000:
        raise ValueError('Replay must use original dev seeds')


def suspicion(chosen, candidates):
    flags = []
    if chosen['task'] == 'END_TURN' and any(c['task'] != 'END_TURN' for c in candidates):
        flags.append('end-turn-with-legal-alternative')
    if chosen['joint_probability'] < .05:
        flags.append('sampled-action-probability-below-0.05')
    return flags


def assert_reproduced(actual, expected):
    for key in ('steps', 'win', 'potion_uses', 'terminated', 'truncated'):
        if actual[key] != expected[key]:
            raise ValueError('Historical replay mismatch: '+key)
    for key in ('reward', 'exit_hp_ratio'):
        if abs(actual[key]-expected[key]) > 1e-9:
            raise ValueError('Historical replay mismatch: '+key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend-root', type=Path, required=True)
    parser.add_argument('--run', type=Path, default=ROOT/'runs/a-v2-ppo-v1')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-probes', type=int, default=24)
    parser.add_argument('--seconds', type=int, default=900)
    parser.add_argument('--probes-from', type=Path,
                        help='Replay previously recorded winning probes with full traces')
    args = parser.parse_args()
    if not 0 <= args.max_probes <= 48 or not 1 <= args.seconds <= 1800:
        raise ValueError('Diagnostic budget out of bounds')
    sys.path.insert(0, str(args.backend_root/'build'))
    import torch
    from sts.env.acorpus import ACorpus, ACorpusSmokeEnv
    from sts.env.lightspeed import _load_backend
    from sts.models.apath import APathActorCritic, encode, batch_samples, TASKS
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError('Original run used CUDA; refusing a different sampling device')
    run = args.run.resolve()
    out = args.output.resolve()
    if out == run or run in out.parents:
        raise ValueError('Diagnostic output must be outside frozen run')
    out.mkdir(parents=True, exist_ok=False)
    corpus_path = ROOT/'projects/battle-initial-states/corpora/a-v2'
    fp = read(run/'fingerprint.json')
    def verify():
        for key, expected in fp.items():
            path = (Path(_load_backend().__file__) if key == 'backend' else
                    corpus_path/key[7:] if key.startswith('corpus/') else ROOT/key)
            if sha(path) != expected:
                raise ValueError('Frozen dependency mismatch: '+key)
    verify()
    checkpoint_path = run/'selected.pt'
    checkpoint_sha = sha(checkpoint_path)
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    if checkpoint['fingerprint'] != fp or checkpoint['iteration'] != 256:
        raise ValueError('Expected frozen selected M0 update 256')
    model = APathActorCritic().to('cuda')
    model.load_state_dict(checkpoint['model'], strict=True)
    model.eval().requires_grad_(False)
    def model_sha():
        h = hashlib.sha256()
        for key, value in model.state_dict().items():
            h.update(key.encode()); h.update(value.detach().cpu().numpy().tobytes())
        return h.hexdigest()
    weights_before = model_sha()
    del checkpoint
    corpus = ACorpus(corpus_path)
    selection, expected = select_cases(run, corpus_path)
    recorded_probes = None
    if args.probes_from:
        prior = read(args.probes_from.parent/'manifest.json')
        if prior['checkpoint_sha256'] != checkpoint_sha or prior['fingerprint'] != fp:
            raise ValueError('Prior probe provenance mismatch')
        recorded_probes = [p for p in read(args.probes_from) if p['counterfactual']['win'] == 1]
        if not recorded_probes or len(recorded_probes) > args.max_probes:
            raise ValueError('Recorded probe count exceeds budget or is empty')
        selection = {p['state_hash']: ['recorded-winning-probe'] for p in recorded_probes}
    cases = {c['state_hash']: c for c in read(run/'evaluation-cases.json')['audit-dev']}
    for key in selection:
        require_dev(cases[key], corpus)
    write(out/'manifest.json', dict(checkpoint_sha256=checkpoint_sha, fingerprint=fp,
          script_sha256=sha(__file__), selected=selection, cases=[cases[k] for k in selection],
          max_probes=args.max_probes, seconds=args.seconds, training=False,
          probes_from_sha256=sha(args.probes_from) if args.probes_from else None,
          selection_scope='Purposive dev subset, not a new evaluation score'))
    deadline = time.monotonic()+args.seconds
    def play(case, trace=True, override=None, reference=None):
        require_dev(case, corpus)
        env = ACorpusSmokeEnv(corpus, scope='experiment-protocol-v1')
        obs = env.reset(corpus.scene(case['state_hash']), case['environment_seed'], purpose='evaluation')
        rng = torch.Generator(device='cuda').manual_seed(case['policy_seed'])
        records = []
        total = 0.
        for step in range(1, 513):
            if time.monotonic() >= deadline:
                raise TimeoutError('Diagnostic deadline reached')
            sample = encode(obs)
            observation_sha = semantic_digest(sample)
            with torch.no_grad():
                dist, value = model(batch_samples([sample], 'cuda'))
                u, j = dist.sample(rng)
            u, j = u.item(), j.item()
            candidates = []
            for a, routes_ in enumerate(sample.routes):
                for b, route in enumerate(routes_):
                    candidates.append(dict(source=a, target=b, task=TASKS[sample.tasks[a]],
                        route=plain(route), source_entity=sample.sources[a], target_entity=sample.targets[a][b],
                        source_probability=dist.source_probs[0,a].item(),
                        conditional_probability=dist.target_probs[0,a,b].item(),
                        joint_probability=dist.probs[0,a,b].item()))
            chosen = next(c for c in candidates if c['source'] == u and c['target'] == j)
            if override and step <= override['step']:
                ref = reference[step-1]
                if observation_sha != ref['observation_sha256'] or plain(sample.route(u,j)) != ref['chosen']['route']:
                    raise ValueError('Counterfactual prefix sampling mismatch')
                if step == override['step']:
                    chosen = next(c for c in candidates if c['route'] == override['route'])
                    u, j = chosen['source'], chosen['target']
            before = obs
            obs, reward, term, trunc, info = env.step(sample.route(u,j))
            total += reward
            if trace:
                records.append(dict(step=step, observation=before, value=value.item(),
                    observation_sha256=observation_sha,
                    candidates=candidates, chosen=chosen, flags=suspicion(chosen,candidates),
                    forced=bool(override and step == override['step']),
                    terminal_observation=obs if term or trunc else None,
                    reward=reward, terminated=term, truncated=trunc))
            if term or trunc:
                break
        else:
            raise RuntimeError('Episode failed to close')
        result = dict(state_hash=case['state_hash'], steps=step, reward=total if term else None,
            win=int(info['task_outcome']=='victory') if term else None, terminated=term,
            truncated=trunc, potion_uses=info['reward_accounting']['potion_uses'],
            exit_hp_ratio=obs['player']['hp']/corpus.rows[case['state_hash']]['state']['player']['max_hp'])
        # Terminal reward only, gamma=1: observed RTG is total at every preterminal state.
        for r in records:
            r['observed_rtg'] = result['reward']
            r['value_minus_observed_rtg'] = r['value']-result['reward'] if term else None
        return result, records
    results, traces, probes = [], {}, []
    try:
        for key in selection:
            result, trace = play(cases[key])
            assert_reproduced(result, expected[key])
            results.append(result); traces[key] = trace
            write(out/(key+'.json'), dict(result=result, steps=trace))
            print(json.dumps(dict(reproduced=len(results), cases=len(selection), state=key)), flush=True)
        # Bounded screen: early choices, rare sampled choices, and flagged end turns.
        # It intentionally includes non-flagged early decisions as diagnostic controls.
        queue = []
        for key, trace in traces.items():
            if expected[key]['win']:
                continue
            flags = [r for r in trace if r['flags']]
            early = [r for r in trace if len(r['candidates']) > 1][:2]
            chosen_steps = {r['step']: r for r in (early+flags[:1]+flags[-1:])}
            for r in chosen_steps.values():
                options = sorted((c for c in r['candidates'] if c['task'] != 'END_TURN'
                                  and c['route'] != r['chosen']['route']),
                                 key=lambda c: -c['joint_probability'])
                if options:
                    queue.append((r['step'], key, options[0]))
        if recorded_probes is not None:
            queue = [(p['step'], p['state_hash'], p['alternative']) for p in recorded_probes]
        for step, key, candidate in sorted(queue)[:args.max_probes]:
            result, branch = play(cases[key], trace=True, override=dict(step=step,route=candidate['route']), reference=traces[key])
            if recorded_probes is not None:
                previous = next(p for p in recorded_probes if p['state_hash']==key and p['step']==step
                                and p['alternative']['route']==candidate['route'])
                assert_reproduced(result, previous['counterfactual'])
            trace_file = f'{key}-branch-{step:04d}.json'
            write(out/trace_file, dict(result=result, steps=branch))
            baseline = expected[key]
            probes.append(dict(state_hash=key, step=step, alternative=candidate,
                trace_file=trace_file,
                baseline=baseline, counterfactual=result,
                reward_delta=result['reward']-baseline['reward'] if result['terminated'] else None,
                caveat='One forced action, original policy RNG stream thereafter; single-seed witness only'))
            write(out/'probes.json', probes)
            print(json.dumps(dict(probes=len(probes), step=step, win=result['win'])), flush=True)
        verify()
        if model_sha() != weights_before or sha(checkpoint_path) != checkpoint_sha:
            raise ValueError('Frozen weights changed')
        write(out/'summary.json', dict(status='complete', reproduced=len(results), cases=len(selection),
            probes=len(probes), winning_alternatives=sum(p['counterfactual']['win']==1 for p in probes),
            weights_unchanged=True, dependencies_unchanged=True, results=results,
            limits=['Purposive dev subset','Single seed','Value residual is not calibration',
                    'End-turn alternatives are suspicion flags, not automatic mistakes']))
    except Exception as exc:
        write(out/'summary.json', dict(status='incomplete', error=repr(exc), reproduced=len(results), probes=len(probes)))
        raise


if __name__ == '__main__':
    main()
