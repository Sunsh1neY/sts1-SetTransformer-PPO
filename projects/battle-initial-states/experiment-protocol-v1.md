# Experiment protocol v1 — owner review draft

Status: **Owner approved formal launch after successful smoke, with one TensorBoard run and separate train/dev namespaces.** Date: 2026-09-19. This explicitly supersedes the earlier stop-at-smoke instruction. The effective reviewed configuration is in [the review sheet](experiment-config-review-v1.md); launch artifacts freeze the final code, config and evaluation cases.

## Question and fixed data

Does the existing A-path Set policy improve over its own untrained initialization on this fixed A-v2 distribution? This is a one-initialization pilot, not Set-versus-MLP or SAB generalization evidence.

Use frozen A-v2 (1,715 states): train 1,240 / dev 288 / holdout 187. Connected components: 84 / 13 / 7. Original A-v1 and all augmentation lineage remain unchanged. Holdout is used only after checkpoint selection.

## Owner-approved sampling

At each training reset, select **A-v1 natural training states with probability 0.5** or **A-v2 augmentation training states with probability 0.5**. Within the selected stratum, sample an eligible connected component uniformly, then a distinct state hash uniformly within that component and stratum. Only components with states in that stratum are eligible; fail on an empty stratum rather than changing weights. This prevents sources with more generated variants receiving more component probability. The 50/50 rule is a reset sampling probability, not a guarantee of equal transition counts or exact finite-batch quotas. Log both reset and transition exposure. Shuffle the full rollout for PPO without category minibatch quotas. Dev and holdout retain their fixed evaluation sets and do not use this sampler. "Natural" names the frozen A-v1 baseline, which still includes its documented reconstruction/configuration and potion projection.

## Approved model, optimizer and budget

Owner-approved architecture is implemented: 370,562-parameter APathActorCritic with two shared SAB blocks, two actor-specific SAB blocks and two critic-specific SAB blocks. Each path has depth four, width 64, four heads and FF128/GELU. Each branch has its own normalization and one-seed PMA; actor source/target heads use actor entity outputs and end-turn uses actor PMA, while value uses critic PMA. Public inputs, action semantics and reward v2 are unchanged. The subsequent formal-launch instruction approves the reviewed settings below. See [implementation evidence](architecture-split-v5.md).

PPO: 8 environments x 128 decisions = 1,024 transitions/rollout; minibatch 64, four epochs (64 Adam steps/rollout); Adam LR 0.00025 linearly annealed over 262,144 transitions, epsilon 0.00001; gamma 1, GAE lambda 0.95, policy/value clip 0.2, entropy coefficient 0.01, value coefficient 0.5, gradient norm 0.5. CUDA FP32, no AMP/TF32. Full details are in the review sheet.

Approved new budget: **one initialization, 262,144 training transitions (256 rollouts), maximum four hours including evaluation and saving**. Completed smoke had a separate 15-minute cap. These are new limits, not renewal of a past budget. Reserve the final hour for evaluation/closure; stop collecting at an update boundary before that reserve. If the full step or evaluation schedule does not fit, report an incomplete/time-limited pilot; do not silently extend or change cases. Existing spec sections 9/10 remain governing.

## Evaluation and checkpoint selection

- Freeze exact case manifests before smoke. Dev: all 288 states x environment seed 0. Evaluate initialization and after 64/128/192/256 updates. Holdout: all 187 states x environment seeds 1 and 2; evaluate initialization and the selected checkpoint once each after selection. Seeds come from unchanged `eval_seeds.json`.
- Use sampled joint actions, with action RNG seed `700000 + environment_seed` reset for each case; same cases/seeds for before/after. Policy probability differences can produce different trajectories despite shared random seeds.
- Primary metric: component-macro mean terminal reward v2 (average seeds/states within each component, then components equally). Select highest dev score, including initialization; ties select earliest checkpoint. Any externally truncated evaluation is reported separately and blocks a complete terminal-score selection claim rather than being scored as defeat or dropped silently.
- Report paired reward difference, win rate, exit HP, potion use and truncation separately for baseline/augmentation, Act, HP band, encounter and augmentation family. Holdout uncertainty uses paired component bootstrap (10,000 resamples, seed 190919, 95% percentile interval); seven components and one initialization limit conclusions.
- Save initial, every eight completed updates, each evaluation checkpoint, selected and final checkpoints. Save RNG, optimizer, active environment replay and all corpus/config/code/backend fingerprints. Resume only an identical fingerprint.

## Approval, smoke and launch gate

After owner approval, implement a dedicated A-v2 admission/sampler adapter using existing backend semantics and APathTrainer; do not run training through diagnostic=True or replace the legacy pool. Freeze and expose the resulting code/config/case hashes.

Smoke: two full 1,024-transition rollouts/updates, followed by a save/load continuation comparison on another 1,024 transitions (reference and restored branches). Verify parameter change, finite loss/gradients, masks, termination/truncation bootstrap, split exclusion, sampler weights, and equal restored trajectories/update. Use the same 262,144-step LR horizon as the formal run. Smoke steps do not count toward the formal budget. Start formal training from a fresh initialization.

Smoke completed successfully. The owner subsequently approved formal training with TensorBoard monitoring. Start from fresh group-0 initialization, execute the stated budget and fixed evaluation schedule, and preserve all run fingerprints. No automatic corpus expansion or budget renewal. SAB generalization remains deferred. See [smoke evidence](experiments/smoke-v1/README.md) and [monitoring plan](tensorboard-plan-v1.md).
