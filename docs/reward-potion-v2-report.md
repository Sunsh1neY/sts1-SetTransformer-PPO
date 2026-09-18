# A-path battle_reward_v2 implementation report

Date: 2026-09-18
Decision: I8 in [decisions.md](decisions.md).
Location: `C:/Users/19091/Desktop/sts2-reward-potion-v2`, branch `codex/reward-potion-v2`.
Status: implemented and CPU regression/runtime validated in the isolated worktree; not merged into main, pushed, or used for a new training run.

## Objective and scope

The owner approved `battle_reward_v2`:

`R = 2 * I(victory) + (HP_end - HP_start) / max_HP_start - 0.05 * potion_uses`.

Intermediate rewards are zero. A genuine terminal transition receives the complete reward exactly once, including the HP term and potion cost on defeat. Starting HP/max HP are from the registered pre-combat candidate. Ending HP includes the backend's existing supported exit effects. External truncation keeps zero immediate reward, an incomplete-return label, and final-observation bootstrap. Gamma remains one. This scalar objective is not a guarantee of lexicographic victory optimization.

The current A-path uses v2 at its environment boundary. The unchanged backend still computes v1, retained as `backend_reward_v1` for diagnostics. Legacy entry points, historical results and `sts/rewards.py` retain their v1 semantics. No pool, model, action layout, observation dimensions or backend source/binary changes were made.

## Implementation

- [Shared v2 accounting](../sts/battle_reward_v2.py): fixed serialized reward identity, terminal component recomputation, episode lifecycle, initial/final HP and inventories, potion event history.
- [A-path environment](../sts/env/apath.py): captures initial state, charges successfully executed legal potion actions, uses explicit backend outcome rather than reward sign, and applies v2 after termination/resource-truncation handling.
- [Trainer](../sts/train/apath.py): saves raw reward accounting in episode records, fingerprints the reward module, stores/checks the reward contract, and validates reconstructed potion counts and accumulated reward during active-environment replay.
- [Evaluation](../scripts/run-a-path-ppo.py): uses the same environment accounting, saves reward identity/components/inputs and reports net HP separately from win rate, exit HP, return and potion use. Source snapshots include the new reward module via fingerprinting.

The current admitted potion set uses explicit drinking actions. Automatic potion consumption and future potion acquisition/generation are not claimed supported by this event recorder. They require additional event instrumentation before admission. A successful legal potion action is counted once; illegal/rejected actions and selection continuations are not charged. New potion mechanisms were not added in this change.

## Verification

Command (PowerShell, from this worktree):

```powershell
$env:PYTHONPATH='C:/Users/19091/Desktop/sts2/third_party/sts_lightspeed/build'
python -m pytest tests/test_battle_reward_v2.py tests/test_apath_training.py tests/test_apath.py tests/test_reward_contract.py tests/test_public_consumables.py tests/test_ppo_training.py -k 'not cuda' -q
```

Result: **92 passed, 1 deselected**. The installed Python is 3.13 with CPU PyTorch 2.6.0. Tests read the existing main-workspace compiled backend; it was not modified or rebuilt.

Coverage includes equal HP loss from different starts, healing and maximum-HP growth, positive-reward failure independent of outcome, cost on defeat, exactly-once terminal payment, incomplete truncation, real legal/illegal potion actions, reset, twenty seeded real battles exercising both victory and defeat with reward recomputation, checkpoint potion replay and reward-contract mismatch rejection, real evaluation records, and existing CPU PPO-update/recovery plus legacy reward/potion regressions. The short optimizer steps are engineering tests, not a substantive training experiment. CUDA was explicitly deselected.

The specification/link checker and `git diff --check` are also run before handoff. The evaluation seeds and training-pool bytes match main. Previously approved I7 governing documentation was copied into this branch so I8 does not discard it; unrelated untracked main documents were not copied or edited.

## Remaining work

No claim of learned potion conservation, higher win rate, or better HP outcomes is made. Those require a separately authorized run after the prerequisite work and version/budget freeze. Required relic-state work remains pending; new A+B source preparation remains deferred under I7. Main still uses its existing code until this branch is integrated.
