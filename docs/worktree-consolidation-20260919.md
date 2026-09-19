# Worktree consolidation — 2026-09-19

## Scope and provenance

The owner requested organization, commits and a push while the existing training
run continues. Consolidation copies completed source and evidence into an isolated
worktree based on main, without modifying the active training checkout.

- Original main baseline: `9635d2c`; original plans were preserved separately in `050a0d6`.
- Active source: `sts2-initial-states`, branch `codex/battle-initial-states`, baseline `9635d2c`.
- [Source snapshot](../projects/battle-initial-states/consolidation-source-snapshot.json)
  records original byte hashes for all copied changed/untracked files. The project
  README receives an additional current-status section after that snapshot.
- The relic and reward branches have no commits absent from main. The relic
  worktree's original A-first plan is preserved at its existing repository-relative
  path. Its unrelated single-line `来了。` edit remains only in that worktree.
- Existing worktrees, ignored backend/reference files, caches, checkpoints and
  live run output stay in place. No raw source archives or proprietary reference
  materials are added to Git.

## Organized deliverables

The [project entry point](../projects/battle-initial-states/README.md) links source
inventory, reconstruction, provenance, schema, runtime evidence and versioned
corpora. A-v1 contains 1,377 states; A-v2 adds 338 for 1,715 total. Their historical
reports retain original hashes and scope. Historical source equivalence and
experiment admission remain separate claims.

The experiment code includes the versioned corpus adapter, strict admission and
sampling checks, the approved 2+2+2 actor/critic architecture, checkpoint
fingerprints, fixed evaluation aggregation and the formal training CLI.
I14/I15 carry the original recorded authorization; this consolidation adds no
new training, sampling, model or reward decision.

Git attributes preserve the frozen project artifacts and launch-fingerprinted
source bytes without Windows newline conversion. They do not relax any runtime
fingerprint validation.

Several baseline source blobs consequently retain CRLF bytes as used by the
live run; those additional baseline diffs are newline-only. Review semantic
changes with `git diff --ignore-space-at-eol` when needed.

## Validation and active run

Focused CPU regressions passed: **85 passed**, covering A-path routing and
gradients, split actor/critic branches, corpus admission/sampling, evaluation,
canonical states, provenance, source compatibility, potion reconstruction and
versioned corpus invariants. Tests ran in the isolated consolidation directory,
with one CPU thread and CUDA hidden. The existing backend binary was reused.

The copied code and corpus files match the active run's recorded fingerprints.
All 28 code/data fingerprint entries were also verified against staged Git
blobs, and all 100 files in the active source snapshot remained unchanged.
The specification checker (`scripts/check-spec-v6.py`) passed.
The active run is `sts2-initial-states/runs/a-v2-ppo-v1`, PID 34096 at inspection;
its status reported `training` and 34,816 transitions at the first snapshot.
This is a time-specific progress observation, not a completion or learning claim.
No process restart, checkpoint rewrite, backend rebuild or budget extension was
performed. No additional GPU smoke or long training was launched.

## Remaining boundaries

- Live run outputs and eventual evaluation results remain local under ignored `runs/`.
- Training improvement, final holdout results and generalization remain unverified.
- The original active worktree remains dirty by design: its exact source snapshot
  is committed through consolidation, while its branch/index and files are preserved.
  Reconcile that checkout after training closure, with a fresh comparison first.
- The older relic worktree keeps its local draft and unrelated edit; no worktree
  deletion or cleanup is part of this operation.
