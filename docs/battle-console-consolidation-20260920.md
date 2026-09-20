# Battle console consolidation and initial-states worktree retirement

## Completed scope

The owner authorized a model-switchable simulator console in a dedicated main-checkout directory, consolidation of useful work, and deletion of the initial-states worktree. Main was clean at `b050e71` before this integration. That commit already contained the corpus, reconstruction/projection and approved A-v2 PPO implementation. They were not replaced with an older checkout. New diagnostic replay, player and interactive-console work was integrated as local commit `02f93f7`; no push was performed.

The maintained console is `tools/battle-console/`, with seven registered compatible M0 checkpoints. The default `selected.pt` is the dev-selected checkpoint at update 256. `final.pt` is also update 256; all model tensors compared equal. File hashes are intentionally different and both original files are preserved. Strict model/backend/corpus fingerprints remain enforced.

## Preservation and removal

- Full source checkout preservation: `runs/worktree-preservation-20260920/` (ignored local artifact).
- All 713 original files, including untracked files, ignored runs, checkpoints, references and cache contents, matched their preserved copies by SHA256 immediately before removal. A service log changed during shutdown; its earlier copy was retained with `.before-close` and the final log was preserved at its original relative path.
- Original run and diagnostic artifacts were copied into main's `runs/` without rewriting checkpoint bytes or historical metadata. Old absolute paths inside historical records remain provenance, not current launch instructions.
- Verified no Python process still referenced the original worktree before removal.
- Removed only `C:/Users/19091/Desktop/sts2-initial-states` through Git's worktree removal operation after verification. Directory absence and worktree deregistration were verified. Its branch was retained; other worktrees were untouched.
- The preservation directory's `.git` file points to retired Git metadata and must not be treated as a live checkout. To recover files, copy them into a newly created checkout without reusing that pointer. The preservation directory is local, ignored, and not a remote backup.

## Verification

- Console/replay/player and scoped corpus/model/evaluation tests: 20 passed, including live CUDA switching initialization -> final -> selected, invalid model rejection and dev-only admission.
- A-path model and training regression tests: 26 passed.
- Desktop browser showed all seven options, successfully switched to initialization, cleared the episode, and restored selected. No mobile checks were requested or performed.
- After removal, service health reported the main root and selected/update 256. The offline player was relocated and served from main as well.

No training was launched or resumed. No model architecture, public input fields, reward, sampler, corpus, or holdout admission was changed. New architectures need explicit adapters and validated contracts; the dropdown does not bypass compatibility checks.

## Current entry points

- Double-click `C:/Users/19091/Desktop/sts2/tools/battle-console/start.cmd`.
- Root convenience launcher: `C:/Users/19091/Desktop/sts2/start-m0-console.cmd`.
- Interactive console: http://127.0.0.1:8767/ after startup.
- Model registry and usage guide: [battle console](../tools/battle-console/README.md).
