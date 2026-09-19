# Experiment configuration review v1

Status: formal-run owner review draft. The owner subsequently authorized execution through smoke completion only; the smoke passed, using this draft's bounded test configuration. Formal training remains unapproved. See [smoke results](experiments/smoke-v1/README.md). Original document preparation only instantiated a CPU model; later smoke execution and its exact fingerprints are recorded separately.

## Architecture — owner-approved 2+2+2 implementation

| Field | Effective value |
|---|---|
| Model | `a-path-shared2-actor2-critic2-pma-pointer-relic-v5`, 370,562 parameters |
| Raw features per entity | CARD 117; ENEMY 774; POTION 21; RELIC 141; PLAYER_GLOBAL 198 |
| Player projection input | 198 + 5 public-context fields = 203; not hidden width |
| Entity projection | Separate biased linear layer per type, output 64; learned type embedding |
| Relations | Current enemy-held-card / bottled-card relation fusion, zero-initialized bias-free 65-to-64 linear layer |
| Encoder | Two shared SAB blocks, two actor-private and two critic-private blocks; six modules total, depth four per path; pre-LayerNorm; 4 heads, 16 dimensions/head |
| FFN | 64 -> 128 -> 64, GELU; dropout 0; LayerNorm epsilon 1e-5 |
| PMA | Separate actor and critic PMA, each with one learned 64-D seed, 4-head attention, residual FF128/GELU and normalization |
| Actor | Task/source dot product and source-conditioned target dot product, scaled by sqrt(64)=8; separate end-turn linear head |
| Value | Shared two-layer trunk then critic-private two-layer SAB/PMA; 64 -> 64 -> 1 with GELU |
| Policy | Source then conditional target; one joint log probability and PPO ratio; exact joint entropy |
| Masks | Environment legal masks before softmax; entity-valid mask separate from candidate legality |
| Initialization | Existing PyTorch constructors; PMA/task-query normal std 0.02; relation fusion zero; no new orthogonal initialization |
| Excluded inputs | No hidden RNG/seed, semantic routing slot, or new model-facing field |

The old unified JSON is not authoritative for A-path topology. The new constructor creates six distinct EntityBlocks in three pairs; the reviewed count comes from the instantiated model. Existing v4 checkpoints are incompatible; no automatic partial loading or weight migration is introduced. Frozen A-v1/A-v2 runtime evidence describes the previous fully shared model and is not re-labeled as validation of v5. New architecture evidence: [architecture-split-v5.md](architecture-split-v5.md).

## PPO and runtime — current values unless marked proposed

| Parameter | Proposed effective value |
|---|---|
| Environment instances | 8, synchronously stepped in the current collector; not eight subprocess workers |
| Rollout | 128 decisions/environment; 1,024 transitions |
| PPO epochs / minibatch | 4 / 64; 16 minibatches/epoch, 64 optimizer steps/rollout |
| Microbatch | Resource-bounded splits of each logical minibatch; weighted gradient accumulation, one optimizer step per logical minibatch |
| Optimizer | Adam, beta1 0.9, beta2 0.999, epsilon 1e-5, weight decay 0, AMSGrad false |
| LR | `2.5e-4 * (1 - completed_transitions / 262144)` before each update; last scheduled rollout starts at 9.765625e-7 |
| Discount / GAE | gamma 1.0; lambda 0.95 |
| Advantage normalization | Per logical minibatch; sample standard deviation plus 1e-8; before microbatch splitting |
| Policy clip / value clip | 0.2 / enabled with 0.2 |
| Value objective | 0.5 * max(unclipped squared error, clipped squared error), then multiplied by value coefficient 0.5 |
| Entropy / value coefficient | 0.01 / 0.5 |
| Gradient norm | Global L2 clipping at 0.5; reject nonfinite gradients |
| KL stop / extra normalization | No target-KL early stop; no reward or return normalization; no reward clipping |
| Reward | `2*victory + (exit_hp-entry_hp)/entry_max_hp - 0.05*potion_uses`; once at true termination |
| Bootstrap | None at true termination; final pre-reset observation at external truncation; GAE does not cross reset |
| Episode bound | Proposed 512 routed decisions, retaining current training limit; prior corpus diagnostics used 128 |
| Resources | Current 448-entity external truncation, 512 hard entities, 4,096 candidate resource cap, 8,388,608 attention elements; preserve generated-card guards and verify they work for A-v2 |
| Numerics | CUDA FP32, AMP off, TF32 off, deterministic algorithms on, one Torch CPU thread; GPU availability/throughput not checked in this documentation task |

## Sampling, seeds and proposed budget

Owner-approved sampling: at each training reset choose natural (the frozen A-v1 training subset) with probability 0.5, or augmentation (A-v2 additions in train) with probability 0.5. Independently within each stratum, choose uniformly among its nonempty connected components, then uniformly among its distinct state hashes in that component. Source identity means connected component for weighting, avoiding duplicate raw-origin weighting. A component can occur in both strata; each stratum has its own eligible component count. For state s in stratum k and component c, P(s) = 0.5 / number_of_components(k) / number_of_states(k,c). Reject an empty stratum; do not silently fall back or renormalize.

Natural contains 1,044 train records across 84 connected components; augmentation contains 196 across 56 connected components. Each stratum receives 50% reset probability regardless of file size. Actual transition share depends on episode lengths; finite reset counts fluctuate. No exact rollout/minibatch category quotas are implied. Dev and holdout remain fixed evaluation sets and retain their existing evaluation aggregation. Sampling is approved but not installed yet; the 2+2+2 architecture is approved and implemented; PPO and budgets remain under review. "Natural" is a baseline label, not a claim of exact historical replay or absence of A-v1 potion projection/configuration.

| Budget / RNG | Proposed value |
|---|---|
| Formal initializations | 1 (`group=0`); a pilot, not multi-seed robustness evidence |
| Formal environment transitions | 262,144 maximum = 256 rollouts = 16,384 optimizer steps |
| Formal wall clock | 4 hours maximum including evaluation/checkpoint/report; reserve final hour for closure |
| Model / sampler / environment RNG / PPO shuffle / policy RNG | 834000 / 831000 / 832000 / 833000 / 835000 |
| Training environment seeds | Unique draws in [10^12, 2^63-1), preserved on resume |
| Smoke | 15 minutes maximum; use RNG group offset 100, formal shapes and LR horizon; 2,048 warmup transitions plus 1,024-transition reference/restored continuation each = 4,096 collector transitions total |
| Evaluation environment seeds | Dev 0; final holdout 1 and 2; unchanged reserved seed file |
| Evaluation policy RNG | 700000 + environment seed, restarted for every state and checkpoint |
| Bootstrap analysis RNG | 190919; 10,000 paired component resamples |

At the full schedule dev costs 5 x 288 = 1,440 episodes and final paired holdout costs 2 x 187 x 2 = 748 episodes, total **2,188 evaluation episodes**. Throughput and completion within four hours are unverified. Time exhaustion yields an explicit partial result, not an increased budget or fewer undisclosed evaluation cases. No past budget is automatically renewed.

## Evaluation definitions

Use all registered dev/holdout states in the fixed manifests. Per checkpoint, average seeds per state, states per connected component, then components equally. This includes baseline and augmentation according to their occurrence within each component; separately report each layer so the mixture cannot conceal opposite movement. Compare the selected checkpoint against its own saved untrained initialization on paired cases.

Use dev only for selection; report all scheduled checkpoints, select maximum mean terminal reward with earliest-checkpoint tie break and initialization eligible. If any dev case truncates, do not treat its zero unsettled reward as a completed return, delete it, or claim a complete ranking. Report the incomplete evaluation and return the unresolved selection issue. Genuine defeats remain genuine outcomes. Runtime exceptions are failures, not defeats.

The 95% paired component-bootstrap interval is descriptive with seven holdout components. It does not account for training-initialization uncertainty; no architecture-superiority or broad generalization claim follows from this pilot. Holdout case results remain unopened until selection; no retuning on them.

## Data fingerprints

| Artifact | SHA-256 |
|---|---|
| A-v1 manifest | `619a3a842c5fe81acc05ff4cea05d00f7a261aef1c729cc65ad55ab9839177ad` |
| A-v2 manifest | `c8806edb5cf6361de5673baecfb6c0650abdef81ad6165a0268a0653d2f1ea06` |
| A-v2 states | `a0f82337269a4458fb8a79ff622d62b7993950a4c2bc32c4d73de49d46c7c2ce` |
| eval_seeds.json | `38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c` |

## Implementation readiness — not yet ready to launch

Post-smoke update: `sts/env/acorpus.py` now provides pinned smoke-only admission and the approved sampler; `APathTrainer(corpus_dir=...)` reuses the collector/PPO/checkpoint implementation and adds corpus fingerprints. Collector labels distinguish natural/augmentation, reset counts survive recovery, and exact CUDA continuation passed. The old-pool path remains available and its five training regression tests passed. The points below describe the original integration gaps; the adapter/collector/recovery portions are now closed for smoke only. Formal admission, full evaluation scheduling and formal-run orchestration remain outstanding. The 3,072-transition smoke branch guard intentionally prevents automatic formal continuation.

1. `APathTrainer.reset()` calls the old `sample_scene()` and `APathEnv`; it cannot consume A-v2. Add explicit corpus admission/adapter and sampler after approval, preserving the old pool and strict purpose checks. Do not train through the development-only RelicEnv reset or merely relabel diagnostic results as admitted.
2. Collector labels currently assume the old pool categories. Add A-v2 lineage/category metrics without changing policy features; extend active-environment replay and checkpoints to contain corpus identity and sampler configuration.
3. Existing runner evaluation cases and script budgets concern the old pool. Implement the exact A-v2 case schedule and reviewed budget, plus separate terminal/truncation reporting. Freeze code/backend/config/case hashes after integration and before smoke; the current training fingerprint lacks A-v2 files.
4. Test split exclusion, exact sampling probabilities, immutable data fingerprints, collector/update and replayed checkpoint continuation before formal launch. The previous 338-state diagnostic run did not exercise PPO or checkpoint recovery.
5. Sampling and the 2+2+2 architecture are owner-approved. Approval is still required for the A-v2 train partition's experiment-specific admission, remaining hyperparameters and new budgets. Record final approval in governing decisions. Material deviations require review; ordinary integration work following approval does not require reopening data engineering.

## Source code inspected

- `sts/models/apath.py`: actual architecture, feature widths, policy/value heads.
- `sts/models/entities.py`: attention/FFN/normalization.
- `sts/train/apath.py`: collector, RNG, optimizer/update, replay checkpoints.
- `sts/train/ppo.py`: GAE and clipped policy/value objectives.
- `sts/env/apath.py`: current source-component sampler and training admission.
- `sts/env/relics.py`: current diagnostic-only corpus-compatible reset.
- `sts/battle_reward_v2.py`: terminal reward contract.
- `scripts/run-a-path-ppo.py`: old-pool orchestration and budget behavior.
