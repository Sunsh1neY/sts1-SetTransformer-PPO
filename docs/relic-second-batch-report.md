# Relic second batch integration

Date: 2026-09-19. Decision I10. Scope audit committed first as `62113cf`, based on first-batch implementation `9d95526`. Worktree: `C:/Users/19091/Desktop/sts2-relic-state-v1`, branch `codex/relic-state-v1`. No merge or push.

## Delivered

The [full static audit](act12-relic-audit.md) classifies every original relic class and reconciles all 180 backend identities. Its baseline remains immutable even though the current registry has expanded. The second batch imports eight ordinary relics into the development-only `RelicEnv`:

| ID | Relic | Verified scope |
|---:|---|---|
| 15 | Bag of Marbles | Opening Vulnerable, Artifact absorption, real attack damage, duration |
| 16 | Red Mask | Opening Weak, Artifact absorption, real intent damage, corrected duration |
| 17 | Clockwork Souvenir | Opening Artifact, actual debuff consumption, no repeated grant |
| 18 | Preserved Insect | Elite-only initial HP reduction; maximum HP preserved; ordinary/boss/event counterexamples |
| 19 | Slaver's Collar | Elite/boss energy, ordinary/event counterexamples, next-battle reset |
| 20 | Black Blood | Victory healing once, HP cap, replacement ownership, failure/truncation behavior |
| 21 | Meat on the Bone | Pre-victory-healing threshold, odd/even max HP, healing order and combinations |
| 22 | Orichalcum | Zero-block trigger, positive-block counterexample, Metallicize interaction |

These are mechanism fixtures, not historical scene acquisition reconstruction. For example, directly configuring a boss relic in an Act 1 diagnostic tests the mechanism without asserting that a particular standard run could obtain it at that exact floor.

## Encoding and compatibility

Registry version is **`relic-state-v2`**. Identity remains **one-hot**: the original 14 columns are preserved as a prefix, followed by the eight new identities. Counter state remains three columns: applicable, known, normalized value. Total input width is **25**, projected to **64**. No state field was added speculatively for these eight relics. Scene conditions and actual effects are already represented in the environment and public player/enemy state.

The A-path model version is `a-path-four-sab-pma-pointer-relic-v2`; its four SAB blocks, four heads, FF128, PMA and source/conditional-target joint PPO remain unchanged. Shape/registry/backend/source fingerprints reject incompatible checkpoint continuation. Historical first-batch example and ledger bytes are preserved as `*-first-batch.json`; the original report now explicitly identifies its historical baseline.

New counter-relic inputs still require explicit counters. Compatibility conversion accepts only the original eight stateless legacy identities; new stateless identities must use the new normalized schema. Burning Blood plus Black Blood is rejected both in Python and the C++ entry because the latter replaces the former.

## Mechanism corrections

The existing backend implements the eight mechanisms, so this change reuses those paths and adds scoped corrections guarded by the new relic-entry flag:

1. **Red Mask duration:** original `RedMask.atBattleStart` applies Weak from the player. The backend default monster-source flag kept it for an extra turn. A real transition test reproduced the mismatch; the new entry now uses the correct source flag.
2. **Single exit healing:** new-entry adapter no longer manually applies Burning Blood before `exitBattle`. It uses the actual backend exit result, avoiding duplicated GameContext healing, and synchronizes final public HP and reward accounting.
3. **Meat on the Bone ordering:** its threshold is evaluated before victory-relic healing, matching original `AbstractRoom.endBattle` followed by `AbstractPlayer.onVictory`. This no longer depends on ownership-list order.
4. **Preserved Insect:** the new entry clamps current HP downward to the target rather than raising already-lower HP. Runtime elite checks passed; the combination with unimported Neow's Lament remains outside this batch's behavior certification.

The fixes are independently written from narrow reference specifications; no original Java implementation was copied. The reward formula remains I8 v2. A real single-action victory example with HP 40/80, Meat on the Bone and Black Blood settles to **64 HP**, with reward **2.3**. [Evidence](evidence/relic-second-batch-checks.json) stores the initial scene, true terminal transition, pre/post exit HP and reward components.

Legacy entries retain their historical behavior. Their internal Burning Blood double-writeback defect is disclosed by the audit; this batch does not silently alter legacy frozen experiments. The fixed admitted A-path pool still uses its existing environment entry; none of the eight new scenes has been admitted to formal training.

## Verification

```powershell
python scripts/regenerate-relic-state-patch.py
./scripts/build-relic-state.ps1
$env:PYTHONPATH='C:/Users/19091/Desktop/sts2-relic-state-v1/third_party/sts_lightspeed/build'
python -m pytest tests/test_relic_batch_two.py tests/test_relic_state.py tests/test_apath.py tests/test_apath_training.py tests/test_battle_reward_v2.py tests/test_unified_entities.py tests/test_entity_input_v3.py tests/test_entity_checkpoint.py tests/test_public_consumables.py tests/test_reward_contract.py tests/test_ironclad_dynamics.py tests/test_ironclad_selection_cards.py -k 'not cuda' -q
```

Result: **592 passed, 1 deselected**, CPU, 16.84 seconds. This includes **352** second-batch reset/step checks (8 relics x 44 Act 1/2 encounters), focused real-effect tests, public encoding/model forward, deterministic action replay, strict rejection, first-batch regression, registered-pool checkpoint/optimizer tests and legacy tests. Reset/step coverage does not prove all encounter/relic/card combinations. CUDA and live original-game differential runs were not performed. No substantial training or learning/generalization claim.

The regenerated additive patch reproduces all three modified backend files from the locked base plus frozen base/enemy patches. Rebuild and registry fingerprint checks passed. Main's binary was not replaced. `eval_seeds.json` and `a-path-training-pool.json` are byte-identical to main; their hashes are recorded in the evidence JSON.

## Remaining and owner review

**22 diagnostic relic imports are complete for the tested scope; 148 possible Act 1/2 relics are not all supported.** The 24 [special-review items](relic-special-review.md) remain unimplemented pending owner review. Later ordinary/stateful candidates need their own verified fields, mechanisms and recovery tests. Run/acquisition effects require configured entry evidence or a future RunEnv, not invented state.

No training-pool expansion, A+B dataset investigation, substantial training, main integration or push occurred. Those remain separate steps under the agreed prerequisite ordering.
