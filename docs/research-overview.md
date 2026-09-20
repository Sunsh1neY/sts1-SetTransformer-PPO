# Research overview

Status: updated 2026-09-20 under decision I16. This overview does not replace [spec-v6](../spec-v6.md) or its [dated amendments](decisions.md).

## Completed milestone

The frozen M0 Set Transformer + PPO policy improved over its own untrained initialization on the fixed admitted A-v2 combat distribution in a one-initialization pilot. Holdout component-macro mean reward increased from -0.45185 to 1.48973 and win rate from 11.56% to 85.33%, with zero external truncations in 374 episodes per policy. See [the result record](m0-learning-result.md) for definitions, source artifacts and limitations.

This is learning evidence for the current policy, not just engineering closure. It does not establish Set superiority over MLP, training-seed robustness, unrestricted generalization or native-game equivalence. Seven holdout components and one training initialization constrain interpretation.

## Current research question

Can controlled changes to actor decision readout and critic pooling improve learning and performance relative to frozen M0, while preserving public observations, action semantics, reward and the admitted distribution?

Proposed directions are critic multi-seed pooling (M1), explicit actor context conditioning followed separately by non-degenerate multi-query readout (M2a/M2b), and their combination (M3). The exact designs and experimental budgets still require review. Width/depth scaling is deferred; no implementation or training is authorized merely by listing these plans.

## Method and baseline

A locked C++ backend supplies public combat observations and legal actions. Python adapters encode cards, enemies, player state, potions and supported relic state. M0 uses two shared SAB blocks and two actor/critic-specific blocks per branch, with width 64, four heads and FF128. The actor scores contextualized source and target entities; its separate single-seed PMA scores END_TURN. The critic has its own single-seed PMA and value head.

A complete action uses a source distribution followed by a conditional legal target distribution; PPO uses joint probability and exact joint entropy. The current reward is battle_reward_v2, balancing victory, initial-max-HP-normalized net HP and potion use. True termination and external truncation retain different bootstrap rules. The [frozen protocol](../projects/battle-initial-states/experiment-protocol-v1.md) is the experiment authority; the legacy 390-configuration pool is not replaced by A-v2.

## Diagnostic evidence and next steps

The [dev replay investigation](../projects/battle-initial-states/m0-dev-replay-v1.md) localized persistent Boss and low-HP failures. It found single-seed alternative winning trajectories and distinguished low-probability sampled mistakes from high-probability source/ordering candidates. These witnesses do not prove a pooling/query bottleneck or expected action advantage.

The [interactive console](../tools/battle-console/README.md) supports frozen checkpoint selection, model execution and manual intervention on fixed dev scenes. It does not train from corrections.

Use dev to refine hypotheses, then freeze ablation contracts and approved budgets. Match unchanged-module initialization where appropriate, report parameter/runtime differences, and distinguish one-run findings from repeated-training evidence. The existing holdout has already been used and must not become an unacknowledged architecture-tuning set. A future evaluation protocol needs approval before further selection.

The owner's learning objective remains understanding representations, attention, policy decisions, gradients and evidence. Full-run navigation, Decision Transformer and broad dataset/backend expansion are not prerequisites for this phase.

## Reproducibility boundary

This documentation update recomputed selected aggregate metrics from existing episode files; it did not execute new training or holdout episodes. Local weights, run artifacts and backend binaries are ignored by Git. A clean-clone reproduction package and cross-initialization robustness remain unverified. Earlier MLP/Set results retain their original scope and do not supply an architecture-superiority conclusion for M0.
