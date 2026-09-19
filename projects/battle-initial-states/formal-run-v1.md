# A-v2 formal run v1

The owner approved launching training after the successful smoke, with train and dev in one TensorBoard run. This note records launch configuration, not a completion or learning claim.

- Run directory: `runs/a-v2-ppo-v1/` in this isolated worktree.
- TensorBoard: http://127.0.0.1:6006/#scalars ; run name `a-v2-ppo-v1`.
- Namespaces: `train/`, `dev/`, `system/`, final `holdout/`, and configuration text.
- Model: 370,562 parameters, shared2/actor2/critic2 SAB architecture v5.
- Fresh initialization group 0; the smoke checkpoint is not continued.
- Sampling: 50/50 natural/augmentation resets, then uniform connected component and state within each stratum.
- Budget: one initialization, at most 262,144 transitions and four hours inclusive, with final-hour closure reserve.
- Fixed dev evaluations at update 0/64/128/192/256; final holdout only after selection.

Launch command:

```powershell
C:/Users/19091/Desktop/sts2/.venv-gpu/Scripts/python.exe -B scripts/run-a-corpus-ppo.py --backend-root C:/Users/19091/Desktop/sts2/third_party/sts_lightspeed --output C:/Users/19091/Desktop/sts2-initial-states/runs/a-v2-ppo-v1
```

The runner refuses to overwrite an existing status file. `status.json` reports phase, evaluation progress and actual training steps; `metrics.jsonl` records each completed update. Checkpoints and raw episode files remain in the run directory, which is ignored by Git. `config.json`, `fingerprint.json`, `evaluation-cases.json` and `source-snapshot.zip` freeze reproducibility evidence. The frozen dataset's historical diagnostic metadata remains unchanged; formal admission is provided by the experiment-scoped wrapper, not by rewriting dataset rows.

Prelaunch checks: 35 tests passed across formal evaluation aggregation/admission, TensorBoard event writing, corpus sampler/admission, model/routing, and existing CPU/CUDA checkpoint recovery. TensorBoard returned HTTP 200. Do not modify fingerprinted code/data while this run is active.

In the dashboard, dev points only appear after all fixed cases finish. Their x-axis is training transitions, not evaluation episode count. Training episode means and dev component-macro means have different populations; compare dev checkpoints against the step-zero dev baseline. `system/phase`: 0 starting, 1 dev, 2 training, 3 holdout, 4 completed, negative values indicate failure/time limit/incomplete evaluation.
