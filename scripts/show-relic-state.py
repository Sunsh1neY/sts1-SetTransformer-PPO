"""Save one real state/action transition and untrained A-path outputs."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
from sts.env.relics import RelicEnv
from sts.env.relic_state import REGISTRY, REGISTRY_HASH
from sts.models.apath import APathActorCritic, batch_samples, encode
from sts.train.apath import fingerprint, plain_route


def main():
    torch.set_num_threads(1)
    torch.manual_seed(0)
    scene = dict(entry_timing='pre_combat_initialization',
        initialization_phase='before_destination_room_entry', act=1, floor=1,
        character='IRONCLAD', ascension=20, player=dict(hp=70, max_hp=80, gold=99),
        deck=['Strike_R'] * 10, relics=['Vajra', dict(name='Pen Nib', counter=8),
            dict(name='Nunchaku', counter=9), dict(name='Ink Bottle', counter=9)],
        potions=[None, None], encounter='JAW_WORM', burning_elite=False)
    env = RelicEnv()
    obs = env.reset(scene, 100123, diagnostic=True)
    model = APathActorCritic().eval()

    def snapshot(obs):
        sample = encode(obs)
        batch = batch_samples([sample])
        with torch.no_grad():
            dist, value = model(batch)
        return dict(relics=obs['relics'], player=obs['player'],
            relic_tokens=[t.features.tolist() for t in sample.entities.tokens if t.entity_type == 'RELIC'],
            entity_valid=batch['entity_valid'][0].tolist(),
            source_probabilities=dist.source_probs[0].tolist(),
            joint_probabilities=dist.probs[0].tolist(),
            action_routes=[[plain_route(r) for r in rs] for rs in sample.routes],
            value=value.item())

    before = snapshot(obs)
    obs, reward, terminated, truncated, info = env.step(0)
    evidence = dict(purpose='Engineering evidence only; untrained model; no learning claim',
        registry=REGISTRY['schema'], registry_sha256=REGISTRY_HASH,
        fingerprint=fingerprint(), initial_scene=scene, environment_seed=100123,
        model_seed=0, before=before, action=0, after=snapshot(obs), reward=reward,
        terminated=terminated, truncated=truncated, transition_info=info)
    output = ROOT / 'docs/evidence/relic-state-example.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
