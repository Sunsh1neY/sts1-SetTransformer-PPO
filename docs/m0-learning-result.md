# M0 learning result — fixed A-v2 distribution

Status: completed one-initialization pilot; documentation verified against local run artifacts on 2026-09-20. This record reports the existing experiment, not a new evaluation.

## Finding

The entity-centric Set Transformer policy trained with PPO improved over its own untrained initialization on the fixed admitted A-v2 evaluation distribution. This establishes a bounded learning milestone and motivates controlled architecture ablations; it does not identify an architectural bottleneck by itself.

| Holdout measure | Own untrained initialization | Dev-selected M0 |
|---|---:|---:|
| Component-macro mean terminal reward v2 | -0.45185 | 1.48973 |
| Component-macro win rate | 11.56% | 85.33% |
| Component-macro exit HP / initial max HP, including defeats | 0.04910 | 0.51719 |
| Component-macro potion uses | 0.18501 | 0.22590 |
| Externally truncated cases | 0 / 374 | 0 / 374 |

Paired reward improvement: **+1.94158**, with the recorded 95% paired-component bootstrap interval **[1.69850, 2.19384]**. The interval resamples seven holdout components (10,000 resamples, seed 190919); it does not quantify uncertainty across training initializations. The reported win rates are not raw wins divided by 374.

## Frozen design

- Corpus A-v2: 1,715 states; train/dev/holdout = 1,240/288/187, split by source connected component (84/13/7 components).
- At training reset: 50% natural / 50% augmentation; independently sample components uniformly within each stratum, then states uniformly. This is not an equal-transition quota.
- Model: 370,562 parameters, shared SAB x2 plus actor SAB x2 and critic SAB x2; width 64, four heads, FF128. Separate one-seed PMA modules; actor entity pointers select source and conditional target, actor PMA scores END_TURN, critic PMA feeds value.
- One fresh training initialization, 262,144 transitions, 256 rollouts. Total recorded duration 9,388 seconds, within the four-hour cap.
- Dev: 288 states, environment seed 0, evaluated at updates 0/64/128/192/256. Select by highest component-macro reward, earliest tie.
- Holdout: 187 states x environment seeds 1 and 2 = 374 episodes per policy. Both policies use the same predefined cases and sampled joint-action semantics. Policy RNG seed is 700000 plus environment seed, restarted per case; matching seeds do not guarantee matching trajectories.
- Mean seeds within each state, then states within each component, then components equally.
- Selected update: 256. Dev reward improved from -0.48383 to 1.41970; dev component-macro win rate from 11.32% to 83.39%.
- Best-dev and final checkpoint model tensors are identical at update 256; serialized checkpoint files remain separately preserved.

The [original protocol](../projects/battle-initial-states/experiment-protocol-v1.md) and [reviewed configuration](../projects/battle-initial-states/experiment-config-review-v1.md) retain the full PPO/evaluation details. Reward is `battle_reward_v2`, not the legacy comparison's v1.

## Source and verification boundary

Local evidence resides under `runs/a-v2-ppo-v1/`: `run-report.json`, `status.json`, `config.json`, `evaluation-cases.json`, `holdout-initial-episodes.jsonl`, `holdout-selected-episodes.jsonl`, `holdout-comparison.json`, checkpoint files and the original source snapshot. These artifacts are ignored by Git and absent from an ordinary clone. This tracked summary is not a substitute for shipping a clean-clone reproduction package.

For this documentation update, case/state/component counts, zero truncations, mean reward and win rate were recomputed from the existing holdout episode records and agreed with the report. The bootstrap interval is quoted from the recorded comparison, not recomputed in this update. No new holdout episode or training step was executed.

## Remaining questions

- One training initialization is not evidence of training-seed robustness.
- Seven holdout components limit source-level uncertainty estimates; multiple states/seeds are not independent source replications.
- Held-out components within this corpus do not establish out-of-distribution or SAB-generalization performance.
- This experiment is not a Set-versus-MLP comparison. Earlier comparison results retain their original, different scope.
- Failures concentrate in some Boss and low-HP dev scenes. Recorded single-action counterfactual wins identify candidate behavioral issues, not a proven pooling/query bottleneck or guaranteed expected improvement. See [diagnostic replay](../projects/battle-initial-states/m0-dev-replay-v1.md).
- The holdout has been used. Future architecture development must not repeatedly tune against it while calling it untouched test evidence.
