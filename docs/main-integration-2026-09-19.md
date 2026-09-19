# Main integration validation — 2026-09-19

Tested source: `f626844`, after fast-forward integration of reward/potion v2 and relic-state v4 into local main.

## Local backend synchronization

The main checkout initially loaded a stale compiled backend without `RelicStateBattleEnv`. Git integration had updated tracked source and patch files, but not the ignored backend source or binary. This was a local build mismatch; no merge conflict was found.

Before modification, 1,334 backend source/support/binary files were archived and individually hash-verified. The backup also contains the two historical documents. Local recovery directory: `C:/Users/19091/Desktop/sts2-backend-backup-20260919-120752`. Intermediate build objects and Git metadata are not included in the archive; the original backend directory was retained.

The committed relic patch passed a forward applicability check, was applied without conflicts, and then passed a reverse check. `scripts/build-relic-state.ps1 -Jobs 2` rebuilt the main checkout backend successfully. The loaded module was under this checkout's `third_party/sts_lightspeed/build`; relic registry, Ironclad contract, Ironclad registry and enemy/potion contract fingerprints all matched.

## Validation

- 5,865 tests passed; one CUDA test was deselected; elapsed time was 101.30 seconds.
- `python scripts/check-spec-v6.py` passed.
- Evaluation seeds and the admitted training pool retained their previous hashes.
- Full JUnit output is preserved locally as `main-tests.xml` in the recovery directory. Machine-readable results and hashes are in `docs/evidence/main-integration-2026-09-19.json`.

The suite covered `test_relic_remaining`, `test_relic_batch_three`, `test_relic_batch_two`, `test_relic_state`, `test_apath`, `test_apath_training`, `test_battle_reward_v2`, `test_unified_entities`, `test_entity_input_v3`, `test_entity_checkpoint`, `test_public_consumables`, `test_reward_contract`, `test_ironclad_dynamics`, and `test_ironclad_selection_cards`, using `python -m pytest` with `-k 'not cuda'` and the main checkout backend on PYTHONPATH.

This confirms the scoped regression suite on the rebuilt main checkout. It does not establish exhaustive relic combinations, original-game parity, learning improvement or generalization. No substantial training or pool expansion was performed.

## Historical records

The owner authorized tracking `docs/current-architecture-dataflow-audit.md` and `docs/handoff-2026-09-14.md` unchanged. Both describe their dated September 14 baseline; their older status and plans are historical evidence, not current authority or new execution authorization.

Compiled modules and local backups remain outside Git. Other machines must build their own backend from the committed patch chain. The owner authorized pushing main after successful validation.
