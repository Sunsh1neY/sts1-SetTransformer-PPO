# Entity-Centric Reinforcement Learning for STS1 Combat

A learning-oriented research project studying **Set Transformers and PPO** in **Slay the Spire 1** Ironclad combat, from entity representations and legal-action routing to reproducible policy evaluation.

**Current milestone:** the frozen M0 Set Transformer + PPO policy has demonstrated learning improvement over its own untrained initialization on the fixed admitted A-v2 distribution in a one-initialization pilot.

**Current work (2026-09-23):** M2a reached update 256 / 262,144 transitions. Its dev-selected comparison with M0 reports a reward difference of +0.0065 and a win-rate difference of -0.049 percentage points; it establishes no reliable overall M2a improvement. I20 approved the M3a, C-W128 and C-D4 Critic experiments. Their latest saved statuses at 02:38 local were 259,072 / 262,144 transitions for M3a, 196,608 / 262,144 for C-W128 (dev phase), and 164,864 / 262,144 for C-D4. Completion and dev selection remain pending in those snapshots. See the [M2a comparison](docs/m0-m2a-completed-comparison.md), [I20](docs/decisions.md#i20--independent-critic-experiments-with-staged-concurrent-launches-2026-09-22) and [Critic protocol](docs/critic-ablation-protocol-v1.md).

**Next question:** under controlled training and evaluation conditions, can Critic pooling or capacity changes improve dev-selected performance over M2a while preserving public observations, action semantics, reward and the admitted distribution?

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

Each branch has a four-SAB path, width 64, four attention heads and FF128; M0 has 370,562 parameters. Actor and critic have separate branch blocks and pooling parameters, with a shared trunk. Source/target tokens already carry state context; the target query is already source-conditioned. M0's actor PMA is used for END_TURN, not every source score.

The policy chooses a source or special action, then a legal conditional target. PPO uses one complete action's joint log probability, one ratio/clipping operation and exact joint entropy.

Current experiment route: [corpus runner](scripts/run-a-corpus-ppo.py) -> [APathTrainer](sts/train/apath.py) -> [A-v2 adapter](sts/env/acorpus.py) -> existing public combat backend, with [APathActorCritic](sts/models/apath.py). The legacy [A-path runner](scripts/run-a-path-ppo.py) and its 390-configuration pool remain separate compatibility paths.

## Next phase: controlled architecture ablations

**M0 remains frozen.** I17-I20 record M2a implementation and evaluation plus the approved Critic experiments. The three Critic runs are incomplete in the latest saved status snapshots; see the [I20 protocol](docs/critic-ablation-protocol-v1.md).

| Variant | Intended change | Latest status |
|---|---|---|
| M1 | Standalone multi-seed Critic PMA on M0 | No M1 execution evidence is recorded in I17-I20 |
| M2a | Explicit source-context conditioning of the Actor query | Completed at update 256; dev comparison found no reliable overall improvement over M0 |
| M2b | Distinct multi-query Actor readout after M2a | Proposal; no implementation or execution approval recorded |
| M3a | Four-seed Critic PMA with the M2a Actor | Approved by I20; latest saved status 259,072 / 262,144 transitions |
| C-W128 | Width-128 private Critic with the M2a Actor | Approved by I20; latest saved status 196,608 / 262,144, in dev phase |
| C-D4 | Four private Critic SABs with the M2a Actor | Approved by I20; latest saved status 164,864 / 262,144 transitions |

The approved Critic runs compare each Critic change conditionally on the M2a Actor. They do not establish standalone M1 effects or additive M1/M2 effects. Critic changes also affect shared representations and the Actor's learning signal through training.

Priorities:

1. Close the three I20-approved Critic runs under their existing budgets and record their dev checkpoint selections.
2. Preserve the approved initialization pairing, data, reward, action/mask semantics and evaluation cases; report parameter count and runtime.
3. Treat each run as a single-initialization result. M3a versus M2a is a conditional Critic comparison; independent or additive effects need the corresponding standalone comparisons.
4. Keep the existing holdout deferred and broad corpus/backend expansion out of this phase.

The existing holdout has already been evaluated and I20 defers it for these runs. Use dev for development and do not repeatedly tune on the old holdout while describing it as untouched. This roadmap does not authorize runs beyond I20 or renew any past budget.

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
