# Entity-Centric Reinforcement Learning for STS1 Combat

A learning-oriented research project studying **Set Transformers and PPO** in **Slay the Spire 1** Ironclad combat, from entity representations and legal-action routing to reproducible policy evaluation.

**Current milestone:** the frozen M0 Set Transformer + PPO policy has demonstrated learning improvement over its own untrained initialization on the fixed admitted A-v2 distribution in a one-initialization pilot.

**Next question:** under controlled training and evaluation conditions, can changes to the actor's decision readout or the critic's pooling improve learning and combat performance?

## Learning evidence

| Fixed holdout metric | Untrained initialization | Dev-selected M0 |
|---|---:|---:|
| Component-macro mean reward | -0.452 | **1.490** |
| Component-macro win rate | 11.56% | **85.33%** |
| Externally truncated episodes | 0 / 374 | 0 / 374 |

The paired reward improvement is **+1.942**, with a recorded 95% component-bootstrap interval of **[1.698, 2.194]**. Evaluation covers 187 holdout states, two environment seeds per state, and seven source connected components. Metrics average seeds within states, states within components, and components equally; win rates are not raw episode fractions. The interval measures case/component variation, not training-initialization uncertainty.

M0 trained for **262,144 transitions**. Dev selected update **256**, which is also the final update; best-dev and final checkpoints have identical model tensors. See the [learning result and evidence limits](docs/m0-learning-result.md) and [frozen experiment protocol](projects/battle-initial-states/experiment-protocol-v1.md).

**Established:** learning improvement in this fixed-distribution pilot. **Not established:** Set superiority over MLP, robustness across training initializations, out-of-distribution generalization, full-run play, or complete original-game equivalence.

## Explore the policy

The [battle console](tools/battle-console/README.md) lets you choose a fixed dev combat, select a frozen checkpoint, run the model step-by-step or automatically, pause for a manual legal action, and hand control back to the model. Model switching resets the episode; interventions do not train the policy.

On the configured Windows machine, double-click [start-m0-console.cmd](start-m0-console.cmd). The launcher opens the local console at http://127.0.0.1:8767/. The [trajectory player](projects/battle-initial-states/player/README.md) and [dev diagnostic report](projects/battle-initial-states/m0-dev-replay-v1.md) make original and single-action alternative trajectories inspectable. These diagnostics are not new aggregate evaluation scores.

## Frozen M0 architecture

```text
Public entities -> type projections / relation fusion
                -> Shared SAB x2
                   |-- Actor SAB x2
                   |     |-- contextualized source / conditional-target pointers
                   |     '-- single-seed PMA -> END_TURN score
                   '-- Critic SAB x2 -> single-seed PMA -> V(s)
```

Each branch has a four-SAB path, width 64, four attention heads and FF128; M0 has 370,562 parameters. Actor and critic have separate branch blocks and pooling parameters, with a shared trunk. Source/target tokens already carry state context; the target query is already source-conditioned. The actor's existing PMA is currently used for END_TURN, not every source score.

The policy chooses a source or special action, then a legal conditional target. PPO uses one complete action's joint log probability, one ratio/clipping operation and exact joint entropy.

Current experiment route: [corpus runner](scripts/run-a-corpus-ppo.py) -> [APathTrainer](sts/train/apath.py) -> [A-v2 adapter](sts/env/acorpus.py) -> existing public combat backend, with [APathActorCritic](sts/models/apath.py). The legacy [A-path runner](scripts/run-a-path-ppo.py) and its 390-configuration pool remain separate compatibility paths.

## Next phase: controlled architecture ablations

**M0 remains frozen.** The designs below are proposals, not implemented models or completed experiments.

| Variant | Intended change | Question |
|---|---|---|
| M1 | Critic multi-seed PMA with explicitly specified aggregation | Does a different value readout help under the fixed budget? |
| M2a | Explicit global-context conditioning of the actor query, initially one query | Does an explicit context path improve source decisions beyond contextualized tokens? |
| M2b | Add genuinely distinct multi-query readout after M2a | Does non-degenerate multi-query fusion provide additional benefit? |
| M3 | Combine the selected M1 and M2 designs | Are their effects complementary, redundant or interfering? |

Before implementation/training, review the exact information flow, aggregation, source/target wiring, parameter counts and shared-trunk effects. A linear average of dot-product query scores can collapse to one effective query; simply adding query vectors is not sufficient. Changing the critic also affects shared representations and the actor's learning signal, even when actor topology is unchanged.

Priorities:

1. Continue dev-only failure diagnosis and counterfactual checks, separating sampling sensitivity from high-probability decision errors.
2. Freeze each ablation's architecture, initialization pairing, budget, metrics and checkpoint-selection rules for owner review. Preserve public inputs, action/mask semantics, reward and sampling when comparing readouts.
3. Run approved smoke checks and bounded, sequential experiments; report both parameter count and runtime, and distinguish pilot results from repeated-training evidence.
4. Evaluate architecture interactions only after the component comparisons are interpretable. Defer width/depth/FFN scaling and broad corpus/backend expansion.

The existing holdout has already been evaluated. Use dev for development; approve the next evaluation protocol before further model selection, and do not repeatedly tune on the old holdout while describing it as untouched. This roadmap **does not authorize new training or renew a past budget**.

## Data and experimental boundaries

- Frozen A-v2: **1,715 states**, split into **1,240 train / 288 dev / 187 holdout** by source connected component. A-v1 remains frozen separately.
- Training reset sampling: **50% natural / 50% augmentation**, component-uniform and then state-uniform within each stratum. This is not an equal-transition quota. PPO shuffles the complete rollout.
- Dev and holdout use fixed evaluation cases, not the training sampler. The legacy 390-configuration pool is unchanged; broader backend support is not unrestricted admission.
- Current reward: **battle_reward_v2**, paid once at true termination: `2 * I(victory) + (HP_end - HP_start) / initial_max_HP - 0.05 * potion_uses`, with gamma 1. Legacy results retain their original reward version.
- True termination does not bootstrap; external truncation bootstraps from the final pre-reset observation. GAE does not cross resets. Errors and truncations are not fabricated defeats.
- Legal actions come from the environment. Public semantic inputs exclude seeds, hidden draw order and routing slot identities. `eval_seeds.json` is immutable; evaluation seeds are in [0,1000), training environment seeds at least 100000.

## Navigation and reproducibility

- [Research overview](docs/research-overview.md): current question and interpretation.
- [M0 learning result](docs/m0-learning-result.md): measurements, protocol and uncertainty.
- [A-v1/A-v2 corpus project](projects/battle-initial-states/README.md): lineage, coverage and frozen artifacts.
- [Battle console](tools/battle-console/README.md): launch, model registration and interaction limits.
- [Documentation map](docs/README.md), [setup](docs/setup.md), and [roadmap](docs/plans/README.md).
- [Earlier MLP/Set comparison](docs/comparison-ppo-report.md): a different, smaller experiment with inconclusive between-architecture differences; do not compare its scores directly to M0 as an architecture claim.

Authority remains [spec-v6](spec-v6.md) with dated amendments in [decisions](docs/decisions.md). Historical progress tables do not override later amendments. The folder name `sts2` is historical; this project studies STS1. Supported entry documentation is English; detailed historical Chinese material remains valid.

`runs/`, checkpoints, `third_party/` and most `reference/` are ignored by Git. The console needs local trusted weights, the configured CUDA environment and matching backend binaries; a normal clone does not include them. A clean-clone end-to-end reproduction package is **not yet verified**. [Consolidation and recovery](docs/battle-console-consolidation-20260920.md) records the move into main and preservation of the retired worktree. No proprietary reference material is published.
