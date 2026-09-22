# Critic experiment recovery — 2026-09-22

The owner requests resuming interrupted training and TensorBoard. All three
training processes and the dashboard process were absent. Original service logs
ended without a Python traceback; original status files still said training.
The machine's recorded last boot was 2026-09-20 14:05:30, not a reboot at this
interruption. No definitive termination cause was established.

| Variant | Last recorded completed update | Durable idle checkpoint | Updates to recompute |
|---|---:|---:|---:|
| M3a | 30 | 24 | 6 |
| C-W128 | 28 | 24 | 4 |
| C-D4 | 3 | 1 | 2 |

New outputs are `runs/critic-{m3a,c_w128,c_d4}-resume-v1/`. The original
directories remain untouched. Strict loader verification checks architecture,
source/data/backend fingerprints, reward contract, resumable boundary and rollout
checksum, and replays active environments to verify observation/action digests
and reward accounting. It restores model, Adam, all recorded RNG states, reset
counters and active environment history. This is not a fresh initialization.

`scripts/resume-critic-ablation.py` preserves the same collector/update and
hyperparameters. The original 262144-transition target remains; previous recorded
active runtime is subtracted from the original 43200-second cap. Every subsequent
completed update now saves an atomic idle `latest.pt`, rather than every eight
updates. Separate provenance records retain the parent checkpoint hash and a
snapshot/hash of the recovery runner without changing frozen historical sources.

Canonical TensorBoard streams in the new directories contain original scalar
events only through the restored step, then new events. Historical suffix events
from updates beyond the durable checkpoint are retained only in the original
run, not spliced into the resumed displayed trajectory. `metrics.jsonl` contains
the valid original prefix plus resumed metrics. `train-episodes.jsonl` in the
resumed directory contains continuation episodes only; do not combine it with
the entire abandoned original suffix when aggregating training episodes.

Dashboard restored on http://127.0.0.1:6008/ via
`scripts/launch-critic-resume-dashboard.py`, showing M0, merged M2a and each
canonical resumed critic experiment. All train/dev/memory tags continue.

Runtime confirmation: all three active environments sets restored successfully.
M3a replayed updates25 and26 and C-W128 update25 reproduced all original recorded
metric fields exactly except elapsed collect/update times. At inspection each
resumed TensorBoard entropy sequence had unique contiguous global steps. These
are observed recovery checks, not a claim about future determinism or completion.
