# M2a runtime and frozen-context diagnostic

## Scope

The owner authorized historical runtime analysis and frozen-weight dev-only
delta-off replay. No training, budget renewal, holdout evaluation, checkpoint
mutation, or deployment change is included.

Entry point: `scripts/diagnose-m2a-context.py`.
Artifacts: `runs/m2a-context-diagnostic-v1/` (local, ignored).
The script rejects existing output directories and verifies the original source,
corpus and backend fingerprints before and after execution, plus checkpoint bytes
and every model state tensor. The run has a 1,800-second diagnostic deadline.

## Runtime finding

M2a changed speed around its update-128 dev evaluation on 2026-09-20.
TensorBoard timestamps place update 128 at 22:47:07 +08:00 and update 129 at
22:52:58 +08:00, with evaluation between them. The intervening wall time includes
evaluation; the following table excludes evaluation and checkpoint saving.

| Rollout window | Mean collect seconds | Mean PPO update seconds | Mean entities | Mean legal actions |
|---|---:|---:|---:|---:|
| 97-128 | 15.3235 | 7.1882 | 27.7342 | 4.9548 |
| 129-160 | 31.9705 | 24.2988 | 27.6580 | 5.1822 |

The same architecture slowed by 2.09x in collection and 3.38x in updating.
Its mean entity count barely changed; legal actions increased by 4.59%.
Across all M2a updates, collect/update durations correlate at 0.9654; their
correlations with mean entities are 0.0277 and -0.0068 respectively.
Matching each update 129-192 to the closest update 65-128 on standardized mean
entities, legal actions and augmentation transition fraction, with replacement,
gives median timing ratios 2.08x and 3.35x. This is a descriptive sensitivity
check, not a causal adjustment or a hardware benchmark.

M0 also has substantial fast/slow phases. The observations do not identify the
added PMA as the cause of the sustained M2a slowdown. Nor do they establish a
specific power, thermal or competing-process cause. Historical GPU/CPU clocks,
power, temperature and utilization were not recorded. The queried Windows System
log returned no events for 22:40-23:00 on that date. Average entities/actions do not
capture padded maximum lengths or attention microbatch splits, so workload effects
are not completely ruled out.

The saved rollout payloads at updates 64, 128 and 192 contain 1,024 samples each;
their maximum entity lengths are 47, 43 and 52. All are below the attention
microbatch threshold: even 64 samples x 4 heads x 52 squared is only 692,224,
against the 8,388,608 limit. These inspected updates did not need resource-driven
microbatch splitting. This check covers those checkpoint rollouts only, not every
historical minibatch or a controlled equal-input hardware benchmark.

## Frozen intervention

- Checkpoint: selected M2a, update 192, strict architecture/state loading.
- Population: all 288 original dev states, environment seed 0, policy seed 700000.
- Normal arm: reproduce historical terminal results and inspect both distributions
  at each visited normal-policy state, without consuming extra policy RNG draws.
- Delta-off arm: a temporary forward hook replaces the residual query MLP output
  with zeros. No parameters are changed or optimized.
- At each normal-arm decision, verify that raw END_TURN logits and conditional
  target logits are identical when the residual is disabled. Softmax probabilities
  may still change through competition among source actions.
- Report joint-MAP changes and total variation on matched states separately from
  whole-episode reward changes. The former uses the normal policy's visitation
  distribution; longer episodes contribute more decision-level observations.
- Delta-off is not M0: all trained M2a representations and other weights remain.
  It removes both state-conditioned and any task-dependent constant contribution
  learned by the residual, so it does not isolate the informational value of
  global context from generic learned query adjustment.
- Identical initial seeds do not hold later random-event consumption fixed after
  trajectories diverge. One policy seed is not an expected-action-value estimate.

## Completed results (2026-09-22)

Both arms completed all 288 cases with zero truncations in 1,268.54 seconds.
All normal-arm historical terminal results reproduced (reward/HP tolerance 1e-9;
exact wins, steps, termination flags and potion counts). The checkpoint SHA256,
all model state tensors and original launch fingerprints remained unchanged.

| Component-macro metric | Normal selected M2a | Delta disabled | Off minus normal |
|---|---:|---:|---:|
| Reward | 1.333776 | 1.053231 | -0.280545 |
| Win rate | 79.5176% | 68.7004% | -10.8172 pp |
| Exit HP / initial max HP | 49.7620% | 43.3419% | -6.4200 pp |
| Potion uses | 0.509002 | 0.509002 | 0 |

Raw wins were 214/288 versus 174/288: 172 both win, 42 normal-only wins,
2 off-only wins, and 72 both lose. Twelve of thirteen components had negative
reward differences. The off-minus-normal reward 95% paired-component bootstrap
interval is [-0.414814, -0.159701] (10,000 resamples, seed 190919). It does not
measure training-initialization or policy-seed uncertainty. Raw paired episode
aggregation independently reproduced the macro reward difference.

Natural component-macro win rate fell from 85.40% to 77.35%; augmentation from
60.54% to 41.90%. Low-HP-family win rate fell from 25% to 6.25%, on only 16 cases.
These are exploratory subgroups with different component counts, not additive
contributions to the overall macro metric.

On 5,083 normal-trajectory decision states, the joint-MAP action changed at 568
(11.17%). Mean joint-distribution total variation was 0.327604 per decision,
or 0.311156 when first averaging within each initial case and then cases equally.
The latter is not component-weighted. Mean absolute END_TURN probability shift
was 0.037318 despite exact unchanged raw END_TURN scores and target logits.
The same-state interventions consumed no additional policy random draws.

## Interpretation and next decision

The residual pathway is used and helps this frozen policy on the fixed dev cases.
Disabling it is not a clean M0 architecture comparison and does not prove that
state-dependent context, rather than generic learned query correction, supplies
the benefit. A frozen fixed/mean-context control would distinguish that question
more directly than immediately adding multi-query; it has not been executed here.
The earlier same-update M0 comparison remains unchanged.

The runtime diagnosis identifies a workload-insufficiently-explained performance
regime change, not a confirmed thermal/power cause or PMA overhead estimate.
Before interpreting another wall-clock-capped architecture experiment, record
time-aligned hardware telemetry and padding/microbatch statistics; that
instrumentation and new training are not part of this completed diagnostic.

Primary outputs are `runtime.json`, `manifest.json`, `normal-episodes.jsonl`,
`delta-off-episodes.jsonl`, `same-state-decisions.jsonl`, `results.json`,
`status.json` and `integrity.json` in the diagnostic directory. Original M0/M2a
training artifacts remain untouched. No holdout cases were used.
