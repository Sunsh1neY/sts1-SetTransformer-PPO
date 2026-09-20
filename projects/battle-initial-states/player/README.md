# Frozen M0 battle replay player

A dependency-free local HTML player, not an original-game client or a training dashboard.

## Open

The generated standalone artifact is `runs/m0-battle-player-v1/index.html`. Open it directly in a browser, or use the local preview at `http://127.0.0.1:8766/` while its loopback-only server is running. No internet, external packages, API service, or model loading is needed for playback. The preview serves only this artifact directory, not the repository.

## Controls and semantics

- Select one of three recorded battles and one of five alternative branches.
- Jump to the intervention, restart, or inspect the true terminal state.
- Each lane has independent previous/next, play/pause, and timeline controls. Speed applies to both lanes.
- Each decision frame shows the pre-action public state and the action about to execute. The following frame is the next decision state. The final frame uses the actual terminal observation and has no fabricated value prediction.
- Gold card borders identify the card used by the displayed action. A green action panel identifies the single forced alternative.
- Probabilities are the frozen model's original source, conditional-target, and joint probabilities, including at the forced step. They are not intervention execution probabilities.
- Player differences refer to the two currently displayed frames, which need not represent matching turns after divergence.
- Expand legal-action probabilities, piles, relic public state, and provenance. Draw-pile list order does not imply draw order.
- This intentionally selected, single-seed counterexample collection is not a new aggregate evaluation, proof of optimality, or evidence of expected improvement.

## Rebuild with fresh output paths

```powershell
& 'C:/Users/19091/Desktop/sts2/.venv-gpu/Scripts/python.exe' -B scripts/replay-m0-dev.py --backend-root C:/Users/19091/Desktop/sts2/third_party/sts_lightspeed --output runs/m0-player-traces-v1 --probes-from runs/m0-dev-diagnostic-v3/probes.json
& 'C:/Users/19091/Desktop/sts2/.venv-gpu/Scripts/python.exe' -B scripts/build-m0-player.py --traces runs/m0-player-traces-v1 --output runs/m0-battle-player-v1/index.html
```

Both commands reject existing outputs. Use new names when repeating. The replay verifies previous probe provenance, strictly reproduces the three baseline and five counterfactual terminal results, saves full branch traces, and checks frozen weights/dependencies after execution. It never imports training code or modifies the original training artifacts. Historical diagnostic manifests retain their original script hashes; newer replay code does not rewrite old evidence.

## Verification and boundaries

- All three original episodes and five winning intervention episodes reproduced their recorded results.
- End-of-run weight and dependency hashes were unchanged.
- Tests cover source/target route labels, selection phases, true terminal frames, matching pre-intervention states, exactly one forced action, offline output, refusal to overwrite, and incomplete-run rejection.
- Browser checks cover independent stepping, battle selection, intervention display, terminal outcomes, and playback. Desktop side-by-side and narrow stacked layouts are provided.
- This version displays recorded trajectories only. It does not allow manually choosing a new action, launching repeated-seed tests from the UI, or controlling the original game.
