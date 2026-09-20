# Battle console

Local interactive combat simulator UI using the existing STS backend and frozen policies. This is not a separate game engine or an original-game client.

## Start

Double-click `start.cmd` in this directory, or `start-m0-console.cmd` at the repository root. The launcher uses the main checkout's `.venv-gpu` and opens http://127.0.0.1:8767/. Reopening reuses a healthy service from this checkout. After reboot or shutdown, run the launcher again. Closing the browser does not stop the service; use the page's shutdown button to release it.

## Model selection

Use the model dropdown and Load button before starting a battle. Switching clears the active battle and logs so a trajectory cannot silently mix policies. Available models are initialization, updates 64/128/192/256, best-dev and final. Default is best-dev (`selected.pt`). In the original M0 experiment, best-dev and final both correspond to update 256 and all model tensors are equal; their checkpoint file hashes differ.

`models.json` is the explicit local trusted checkpoint registry. Entries specify ID, label, repository-relative checkpoint path, exact SHA256 and architecture version. Checkpoints contain Python serialization and must come from trusted local runs. The service verifies each checkpoint's registered hash, checkpoint fingerprint, current runtime/backend/corpus fingerprints, and strict model parameter topology. No arbitrary checkpoint upload is exposed.

This release supports the current APathActorCritic v5 architecture only. Registering another compatible checkpoint requires recording its real SHA256 and retaining its expected fingerprint. A new M1/M2 architecture requires an explicit model adapter and its own validated contracts; do not bypass fingerprint checks to make it load.

## Combat controls

Select one of 288 fixed dev scenes, start/reset, step the model or auto-run. Pause and choose a complete legal action (including target) to intervene; resume the frozen model afterward. Manual choices are labeled and retain the original model proposal. Fixed seeds are environment 0 and policy 700000. All tabs share one session; use one controlling tab. Stale revisions are rejected.

Export saves the current public state and action log, not full per-step observations. Reset/switch/shutdown discard the in-memory session. No undo, branching, custom-state editor, holdout access, training, or multi-seed batch evaluation is implemented.

## Directory layout

- `server.py`: loopback HTTP service, frozen model loading and dev-only environment admission.
- `console.html`: desktop interactive UI.
- `models.json`: seven registered checkpoints, no weights stored in Git.
- `launch.py`, `start.cmd`: start/reopen helpers.
- `../../scripts/m0-console.py`, `../../scripts/launch-m0-console.py`: compatibility entry points.
- `../../runs/a-v2-ppo-v1/`: original immutable training evidence and weights.
- `../../runs/m0-player-traces-v1/`, `../../runs/m0-battle-player-v1/`: recorded counterfactual evidence and offline player.
- `../../runs/worktree-preservation-20260920/`: complete retired worktree preservation, including ignored files. Its `.git` file is historical metadata, not a usable checkout registration.

Startup failures are logged under `runs/m0-console-service/`. Desktop interaction only was verified; mobile verification was explicitly excluded. No remote publishing is performed.
