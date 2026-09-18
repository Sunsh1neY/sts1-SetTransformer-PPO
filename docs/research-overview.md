# Research overview

Status: current framing, agreed on 2026-09-16. This is an overview, not a replacement for [spec-v6](../spec-v6.md).

## Question and learning objective

Can an entity-centric Set Transformer policy trained with PPO improve its expected combat return over its own untrained initialization on a fixed, admitted STS1 combat distribution?

The owner's primary objective is to understand representation, attention, policy decisions, gradients, and experimental evidence. A mentor-readable research snapshot supports that objective. The first stage should have a narrow, achievable question; it does not require an architecture-superiority claim.

## Method

A locked headless C++ backend provides combat observations and legal actions. Python adapters expose approved public information. Cards, enemies, player state and supported relics are encoded as entities. The current A-path encoder uses four SAB layers (64 dimensions, four heads, FF128) and single-seed PMA.

The actor selects a source/special action and then its conditional legal target. The complete action is decoded into one environment step. PPO uses the joint action probability and exact joint entropy. The critic estimates return; terminal and externally truncated trajectories have different bootstrap rules. See the [source-backed integration chain](a-path-main-integration-report.md) and [entity contract](unified-entity-interface.md), whose historical sections must be read with their version labels.

## What can be said now

- A-path integration and short engineering closure are recorded in the integration report. This establishes implementation evidence, not broad learning or generalization.
- Earlier frozen MLP/Set experiments report within-policy improvement and inconclusive between-architecture differences. They used a different task/architecture contract from the current A path.
- The archived A-path run and its status/report files exist locally. Their original fingerprints and outcomes must be audited before presenting a recomputed result or resuming a checkpoint on any backend.
- There is no new training result from this repository cleanup.

## How the question will be evaluated

For a later authorized evaluation, compare initial and trained policies on the same predefined cases using the same action-sampling semantics and task contract. Report all available initializations, mean combat return, win rate, conditional exit HP, and unresolved episodes. Distinguish case variation from training-initialization uncertainty; new random seeds alone do not prove unseen-deck generalization. Recover usable historical evidence before deciding whether new training is necessary.

The A-path reward is now `battle_reward_v2`: `2 * I(victory) + (HP_end - HP_start) / max_HP_start - 0.05 * potion_uses`, paid once at true termination (I8). It balances victory, net HP and potion conservation; it does not strictly prioritize win rate. Legacy paths and historical results retain `battle_reward_v1`. See the [v2 implementation report](reward-potion-v2-report.md).

## Next boundary

Preserve the existing registered pool for this stage. Relic mechanisms and faithful Act 1/2 combat are the next development priority, with preparation retained in [pending plans](plans/README.md). Before expansion, turn that aspiration into explicit scene, state, mechanism, recovery, and admission criteria. Full-run navigation and Decision Transformer remain later work.

## Limits of this snapshot

No clean-machine reproduction, fresh full regression, checkpoint recovery, statistical recomputation, or new mechanism validation has been performed merely by rewriting these documents. The frozen MLP/Set study is limited in scope, has unequal parameter counts and deck overlap, and does not establish superiority or equivalence. Current coverage lists are not proof of all card/relic/enemy combinations.
