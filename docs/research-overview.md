# Research overview

Status: updated 2026-09-23 under [I17-I20](decisions.md), preserving I16's completed M0 milestone. This overview does not replace [spec-v6](../spec-v6.md) or its dated amendments.

## Completed milestone

The frozen M0 Set Transformer + PPO policy improved over its own untrained initialization on the fixed admitted A-v2 combat distribution in a one-initialization pilot. Holdout component-macro mean reward increased from -0.45185 to 1.48973 and win rate from 11.56% to 85.33%, with zero external truncations in 374 episodes per policy. See [the result record](m0-learning-result.md) for definitions, source artifacts and limitations.

This is learning evidence for the current policy, not just engineering closure. It does not establish Set superiority over MLP, training-seed robustness, unrestricted generalization or native-game equivalence. Seven holdout components and one training initialization constrain interpretation.

## Current research question

Can Critic pooling or capacity changes improve dev-selected performance over M2a while preserving public observations, action semantics, reward and the admitted distribution?

M2a reached update 256 / 262,144 transitions. Its paired dev comparison with M0 showed a small reward point-estimate increase and a slightly lower win-rate point estimate; no reliable overall M2a improvement was established. I20 approves M3a, C-W128 and C-D4 as independent Critic changes on the M2a Actor. The latest saved statuses (2026-09-23 02:38 local) were 259,072 / 262,144 transitions for M3a, 196,608 / 262,144 for C-W128 (dev phase), and 164,864 / 262,144 for C-D4. See the [M2a comparison](m0-m2a-completed-comparison.md) and [I20 protocol](critic-ablation-protocol-v1.md). M1 and M2b have no execution evidence in I17-I20. The Critic runs do not isolate standalone M1 effects or prove additive effects.

## Method and baseline

A locked C++ backend supplies public combat observations and legal actions. Python adapters encode cards, enemies, player state, potions and supported relic state. M0 uses two shared SAB blocks and two actor/critic-specific blocks per branch, with width 64, four heads and FF128. The actor scores contextualized source and target entities; its separate single-seed PMA scores END_TURN. The critic has its own single-seed PMA and value head.

A complete action uses a source distribution followed by a conditional legal target distribution; PPO uses joint probability and exact joint entropy. The current reward is battle_reward_v2, balancing victory, initial-max-HP-normalized net HP and potion use. True termination and external truncation retain different bootstrap rules. The [frozen M0 protocol](../projects/battle-initial-states/experiment-protocol-v1.md) retains its original scope; the legacy 390-configuration pool is not replaced by A-v2.

## Diagnostic evidence and next steps

The [dev replay investigation](../projects/battle-initial-states/m0-dev-replay-v1.md) localized persistent Boss and low-HP failures. It found single-seed alternative winning trajectories and distinguished low-probability sampled mistakes from high-probability source/ordering candidates. These witnesses do not prove a pooling/query bottleneck or expected action advantage.

The [interactive console](../tools/battle-console/README.md) supports frozen checkpoint selection, model execution and manual intervention on fixed dev scenes. It does not train from corrections.

The M2a dev comparison is complete; see its [comparison report](m0-m2a-completed-comparison.md) for its paired cases and uncertainty limits. Continue only the three I20-approved Critic runs, use their frozen dev checkpoint-selection schedule, and report parameter/runtime differences. Treat these as single-initialization evidence. The existing holdout has already been used and remains deferred for this phase.

The owner's learning objective remains understanding representations, attention, policy decisions, gradients and evidence. Full-run navigation, Decision Transformer and broad dataset/backend expansion are not prerequisites for this phase.

## Reproducibility boundary

The 2026-09-20 M0 update and 2026-09-22 M2a comparison recomputed selected aggregates from existing episode files. The 2026-09-23 status update read the latest saved Critic run status files; it did not recompute Critic metrics, train, or evaluate. Local weights, run artifacts and backend binaries are ignored by Git. A clean-clone reproduction package and cross-initialization robustness remain unverified. Earlier MLP/Set results retain their original scope and do not supply an architecture-superiority conclusion for M0.
