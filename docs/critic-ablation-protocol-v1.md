# Critic ablation protocol v1

Approved on 2026-09-22: independent M3a, C-W128 and C-D4 runs, launched in that
order after each minimal path smoke passes. Concurrent execution is authorized.
The owner explicitly raises each run's wall-clock cap to 43,200 seconds (12h),
retaining a 3,600-second closure reserve and target 262,144 transitions.
Do not extend limits automatically. Wall time under GPU contention is not an
architecture efficiency comparison.

All variants inherit the M2a actor, width-64 projections and two shared SABs.
Actor weights and shared trunk train normally; critic modifications indirectly
affect them through gradients and advantages.

| Variant | Private critic SABs | Width / FFN | Heads | PMA seeds | Value head |
|---|---:|---|---:|---:|---|
| M3a | 2 | 64 / 128 | 4 | 4 | 256 -> 64 -> 1 |
| C-W128 | 2 | 128 / 256 | 4 | 1 | 128 -> 128 -> 1 |
| C-D4 | 4 | 64 / 128 | 4 | 1 | 64 -> 64 -> 1 |

C-W128 alone adds a 64->128 critic entry projection. M3a shares PMA attention,
FFN and normalization across its four distinct seeds, retains all four outputs
and concatenates in fixed seed order. No dynamic critic queries, inter-summary
SAB, diversity loss, combined variants, or encoder expansion is included.

Each constructor builds the complete fresh M2a first, then changes only the
critic modules. Shared and actor parameters are therefore exactly paired at
seed 834000; the minimal smoke checks all unaffected tensors against fresh M2a.
No trained model initializes these experiments. M3a preserves the original first
seed and initializes three additional seeds independently.

Preserve M0 PPO settings: group 0; eight environments x128 steps; four epochs;
minibatch64; learning rate 2.5e-4 linearly decayed against262144 transitions;
gamma1; GAE .95; joint policy clip .2; value clipping; entropy .01; value .5;
gradient clip .5; Adam eps1e-5; CUDA FP32; no TF32, AMP or dropout; one CPU thread.
A-v2 stays fixed: reset natural/augmentation 50/50, uniform components within
each stratum then uniform states. No input, reward, masks or routing changes.

Dev stays fixed at288 cases, original environment/policy seeds and component
macro metrics. Evaluate at updates0/64/128/192/256; select highest dev reward,
earliest tie. Holdout is deferred, not used for iterative architecture selection.
Use the existing benchmark only with an explicitly recorded final comparison.

Smoke uses separate group100 weights, 2 environments x8 steps, one full PPO
update, strict checkpoint restore including active environment replay, actor
initial-pairing check, finite loss/gradient checks, critic gradient coverage, and
a bounded real dev terminal rollout. It is discarded; formal runs start fresh.
A smoke failure blocks that variant's formal launch. No broad regression suite.

Save source snapshots and exact model/code/corpus/backend fingerprints.
Each run writes all train/dev/system namespaces into one TensorBoard run.
Preserve historical M0/M2a fingerprinted code and event files.
