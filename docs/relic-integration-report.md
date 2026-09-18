# Relic state integration — first implementation slice

Date: 2026-09-19. Decision: I9. Base: reward-v2 commit `1e95005`.
Worktree: `C:/Users/19091/Desktop/sts2-relic-state-v1`.
Branch: `codex/relic-state-v1`. Not merged or pushed.

## Result

The existing eight relics and six counter representatives now have a strict diagnostic path through backend initialization, public observation, one-hot encoding, the unchanged A-path backbone, real transitions and deterministic action replay. This is the first implementation slice, not certification of every Act 1/2 relic or original-game parity. The fixed training pool remains unchanged.

The six added relics are Pen Nib, Nunchaku, Happy Flower, Incense Burner, Ink Bottle and Sundial. Their existing simulator counters and trigger logic are reused. No new implementation of those trigger rules was introduced. The additive C++ adapter patch exposes `RelicStateBattleEnv`; existing backend classes retain their original whitelist/protocol. The adapter fixes Pen Nib boolean-status observation, which previously attempted a numeric map lookup and raised `map::at` when this newly reachable state was observed. Its internal counter sentinel `-1` is exported as public progress `9`, never as an unexplained negative feature.

## Representation

[Registry](../sts/env/relic-state-registry.json) fixes 14 identity columns, preserving the original eight as the prefix, followed by the six counter relics in the order above. There is no relic identity embedding. Each owned relic is one token:

| Feature group | Width | Meaning |
|---|---:|---|
| Identity one-hot | 14 | Exactly one registered identity |
| Counter applicable | 1 | Whether this relic has a counter |
| Counter known | 1 | Whether its counter is available under this contract |
| Counter / period | 1 | Exact cyclic progress under the relic-specific scale |
| Raw width | 17 | Projected by the existing type-specific linear layer to 64 |

The first eight have `(applicable, known, value) = (false, false, null)` in public state and zero numeric state features. A real zero counter has `(true, true, 0)`. This slice requires all six counters to be known; missing values are rejected, including at initialization. It does not introduce a generic unknown-state escape hatch. Unused speculative fields such as `spent`, `remaining_uses` and binding references are not added yet.

Counter periods are 10, 10, 3, 6, 10 and 3 respectively. Input counters refer to **before combat initialization**. Happy Flower and Incense Burner can advance/trigger during initialization, so their first observed value need not equal their input value. Backend battle-exit exports use the actual counters written back by `exitBattle`.

All tokens use the existing four SAB layers, width 64, four heads, FF128 and single-seed PMA. Source/conditional-target joint PPO is unchanged. Passive relics are not action candidates. The A-path model version changes to `a-path-four-sab-pma-pointer-relic-v1`. Legacy entity encoding remains 10-dimensional unless the explicit new encoder is supplied. A-path converts original stateless observations into the new 17-dimensional encoding; old checkpoints are not compatible resumes, and source/registry/backend fingerprint checks remain strict.

## Implementation map

- [Backend patch](../patches/lightspeed-relic-state.patch): additive adapter input/output and separate backend class, not a rewrite of combat mechanics.
- [Registry validation and encoding](../sts/env/relic_state.py): exact keys, identity checks, range validation, explicit applicability and one-hot columns.
- [Diagnostic environment](../sts/env/relics.py): reuses existing normalization/selection/routing and reward v2, rejects training admission, records pre/post relic states.
- [Shared entity adapter](../sts/env/entities.py): explicit encoder/dimension parameters, with original defaults retained.
- [A-path model](../sts/models/apath.py): 17-to-64 relic projection; existing attention/action/value design retained.
- [Trainer fingerprints](../sts/train/apath.py): includes the new registry, adapter, encoder and backend patch.
- [Example generator](../scripts/show-relic-state.py) and [actual example](evidence/relic-state-example.json): raw relic states, token rows, entity mask, source/joint probabilities, value and next state from an untrained model.

## Verification

Built a separate backend from the locked local upstream clone and pinned JSON/pybind11 revisions. The base, enemy/potion and relic patches apply in order to a temporary Git index and reproduce the built adapter. Neither the main backend nor its binary was overwritten. A Windows CRLF patch-generation issue was detected by this clean-chain check and fixed by storing the additive patch with LF endings.

Rebuild with `scripts/build-relic-state.ps1`. Registry fingerprint checks fail closed.

```powershell
$env:PYTHONPATH='C:/Users/19091/Desktop/sts2-relic-state-v1/third_party/sts_lightspeed/build'
python -m pytest tests/test_relic_state.py tests/test_apath.py tests/test_apath_training.py tests/test_battle_reward_v2.py tests/test_unified_entities.py tests/test_entity_input_v3.py tests/test_entity_checkpoint.py tests/test_public_consumables.py tests/test_reward_contract.py tests/test_ironclad_dynamics.py tests/test_ironclad_selection_cards.py -k 'not cuda' -q
```

Result: **175 passed, 1 deselected**, CPU, 12.85 seconds. CUDA was not tested.

Coverage includes individual real effects for all eight originals; counter boundaries and non-trigger cases; Pen Nib single consumption and interaction with Vajra; Nunchaku/Ink Bottle interaction; entry and later turn triggers; real shuffle; invalid/missing/duplicate/special inputs; zero versus inapplicable; unchanged legacy rejection; truncation without fabricated exit; one-hot/no-relic/padding/permutation behavior; separate Actor/Critic counter-gradient paths; the actual PPO loss and an optimizer step; serialization and deterministic action replay for all six counter relics; actual exit export and next-battle initialization; and existing registered-pool checkpoint/update regressions.

The six counter replay tests reconstruct from serialized initial scene/seed/actions and compare next observations, rewards and exit state. They are **not** a claim that the formal APathTrainer now admits counter-relic scenes. The formal trainer's save/load test still uses the unchanged admitted pool. No substantial training was launched; no learning improvement is claimed.

Evaluation seeds and the admitted pool are byte-identical to main. Main's dirty documents and unrelated untracked files were preserved.

## Remaining work and owner review

[Audit ledger](evidence/relic-audit-ledger.json) inventories 180 non-sentinel upstream entries and source occurrences. Fourteen have this scoped implementation evidence. Other entries remain explicitly unimported; source occurrence does not prove correct behavior. Full original-game catalog comparison, per-relic reference arbitration and exhaustive combinations remain pending. Therefore the original plan's full R0 audit gate is not declared complete.

Next ordinary candidates from the plan are Bag of Marbles, Red Mask, Clockwork Souvenir, Preserved Insect, Slaver's Collar, Black Blood, Meat on the Bone and Orichalcum. Their required public state and triggers must be audited before adding columns or opening diagnostics.

Special review items are recorded before implementation: Bottled relics (exact card-instance binding), Gambling Chip/Nilry's Codex (selection/generation), Frozen Eye/Runic Dome (information visibility), and Potion Belt (capacity/action layout). This list is not approval, and further special cases may be found. Present concrete field/action changes and effects on existing contracts to the owner before implementing those parts.

Reward v2 remains fixed. New A+B source work, scene admission and retraining follow the agreed prerequisite order; no dataset work or pool expansion occurred in this slice.
