# A-v2 split-architecture smoke v1

Status: **passed; formal training not started**. Date: 2026-09-19.

## Scope and configuration

NVIDIA GeForce RTX 3060 Laptop GPU, PyTorch 2.6.0+cu126, deterministic FP32, AMP/TF32 disabled. Model: `a-path-shared2-actor2-critic2-pma-pointer-relic-v5`. Training reset uses the pinned A-v2 manifest and 50/50 natural/augmentation, independently component-uniform then state-uniform. Admission is explicitly smoke-only; diagnostic reset is not used and the legacy pool is unchanged.

Eight environments x 128 decisions; four PPO epochs, minibatch 64; LR horizon 262,144 transitions. RNG group offset 100. Two warmup rollouts/updates, checkpoint, then one reference continuation and one restored continuation. The 900-second smoke completed in **100.89 seconds**.

## Verified results

- 4,096 physically collected transitions, including duplicate recovery verification; 3,072 logical transitions on each final branch.
- 192 optimizer steps per final branch (128 shared warmup steps, 64 continuation steps). The two physical continuation executions both completed; there were 256 physical optimizer steps overall.
- Model parameters changed, losses and gradients remained finite, and legal source/target routes executed through the real backend.
- Restored next-rollout actions, log probabilities, values, rewards, GAE advantages/returns, termination/truncation flags and next values matched exactly.
- Final model tensors, optimizer state, action/sampler/environment/shuffle RNG states and active observation digests matched exactly.
- Checkpoint files: `after-two-updates.pt` and `restored-final.pt`. Full code/backend/corpus fingerprints and exact case-manifest hash are in `smoke-report.json`.
- A fourth logical rollout is rejected by the smoke budget guard; no formal run follows.
- Evaluation cases were fixed but not run: 288 dev cases and 374 holdout cases. No holdout outcomes were inspected.

The single logical trajectory completed 211 episodes (154 defeats, 57 victories), with zero observed truncations. These smoke outcomes are not learning evidence. External truncation was covered by a dedicated one-action adapter test and GAE mathematical tests, rather than claimed from nonexistent smoke truncations.

Observed resets (including the initial eight and currently active episodes): natural 109, augmentation 110. Logical transition counts: natural 1,909, augmentation 1,163. Thus equal reset probability does not imply equal transition exposure; augmentation accounted for approximately 37.86% of transitions in this tiny run.

## Checks

- Adapter admission/sampling tests plus model/routing tests: **27 passed**.
- PPO/GAE mathematical tests: **32 passed**.
- Existing A-path training/admission and CPU/CUDA recovery regressions: **5 passed**.
- Frozen A-v1 and A-v2 fingerprints verified unchanged.

Authoritative evidence: [smoke-report.json](smoke-report.json). This is collector/update/recovery evidence, not a full training experiment, learning improvement, or SAB generalization result. The full formal evaluation scheduler remains to be implemented before any approved formal run.
