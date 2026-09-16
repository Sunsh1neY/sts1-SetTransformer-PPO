# Repository inventory and evidence gaps

Inspection date: 2026-09-16. Baseline: local `main` at `de951cdde082d9d1dd3aae6c8b4da6255f1401db`. This inventory accompanies [spec-v6](../spec-v6.md) and decision I6; it is not a new experimental report.

## What was established

- The tracked tree was initially clean. Two pre-existing untracked files, `docs/current-architecture-dataflow-audit.md` and `docs/handoff-2026-09-14.md`, are preserved byte-for-byte and excluded from the cleanup commit.
- A-path is integrated locally. Source inspection confirms its trainer/model/environment path and separate fingerprint list. The downloaded refactor proposal's remote `e967255` baseline is stale for this checkout.
- The frozen comparison run exists under `runs/comparison-ppo-20260912-gpu-v1`, with its source ZIP, plan, summary and per-model directories.
- The historical A-path run exists under `reference/desktop-repo-archive-20260914/original-directories/sts2-integration/runs/a-path-ppo-20260914-v1`. Its status file reports `completed_within_limits`, with per-initialization stopping reasons. This is an observed historical status field, not a fresh restoration, recomputation or learning verdict.
- The existing desktop archive contains its Git bundle, manifest, original directories and ZIP copies. Representative artifacts were hashed, not comprehensively reverified or duplicated.
- Legacy source archivers read root v4/v5 as files to package; they do not parse those documents into training parameters. The minimal fix reads their explicit archive paths and keeps the active v6 file required. The current A-path source/fingerprint logic is unchanged.

Exact paths, hashes and historical per-initialization step counts are in the [machine-readable inventory](repository-inventory.json). Document movements and source/result hashes are in the [migration manifest](../archive/migration-manifest.json). Checks performed for this cleanup are recorded in the [completion report](repository-cleanup-report.md).

## Source identity and preservation

The prior README and agent rules are preserved as byte-identical snapshots. Moved historical documents retain their substantive content; where line endings or relative Markdown navigation needed adjustment, the manifest records the transformed hash and original Git source. Original runs, checkpoint files, historical source ZIPs, task/reward versions, backend, registered pool and `eval_seeds.json` are not rewritten.

The relic preparation document was copied from the owner's Downloads folder and hashed. It is retained as a pending source, not executed or certified. Its older baseline is called out in the pending-plan index.

## Remaining work, in priority order

1. At the next mechanism stage, turn the Act 1/2 fidelity goal into explicit relic/state/recovery/scene admission criteria, using the existing preparation.
2. Audit the located A-path run's original source/backend/checkpoints and raw results before promoting any learning claim or planning replacement runs.
3. Provide and test an accessible clean-clone evaluation/report package; ignored desktop artifacts alone are insufficient public reproduction instructions.
4. Continue English migration when a detailed document is actively revised. Broad translation is not required to finish this cleanup.

No full-game equivalence, newly passed Gate, new architecture advantage, broad generalization, or new training result is claimed. Missing evidence stays visible rather than being filled with inferred results.
