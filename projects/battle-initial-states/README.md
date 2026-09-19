# Battle initial-state project

## Consolidated status (2026-09-19)

Start with the [worktree consolidation report](../../docs/worktree-consolidation-20260919.md).
The A-v2 experiment is running under the owner-approved [formal protocol](formal-run-v1.md)
and I15. Its 2+2+2 architecture, experiment-specific admission and launch supersede
the earlier milestone statements below only within this experiment. A-v1 has
1,377 states; A-v2 has 1,715, including 338 augmentations. The legacy 390-configuration
pool remains separate. Training completion and learning improvement are not yet established.

The [reconstruction engine plan](reconstruction-engine-plan.md) and
[original A-first proposal](../../docs/a-first-initial-state-dataset-plan.md)
are historical planning inputs; their earlier state counts and pending-launch
statements are not the current run status. Frozen evidence files retain their original bytes.

## Original milestone record

Versioned corpus entry point: [A-v1 baseline and A-v2 coverage augmentation](corpora/README.md). Use the versioned `states.jsonl` files for stable inputs; project-root historical artifacts remain available for provenance.

Latest training-chain evidence: [A-v2 CUDA smoke v1](experiments/smoke-v1/README.md), passed with the 2+2+2 model and exact checkpoint recovery. Formal training has not started.

Subsequent owner-approved launch: [formal run v1 and TensorBoard monitoring](formal-run-v1.md). Consult the run's live `status.json` for progress; the smoke statement above describes the earlier milestone.

This folder holds the small-corpus pilot plan and its audit. It is a project inside the existing repository, not a separate simulator or training system.

Current deliverable: [supported-potion projection report](potion-projection-report.md), dated 2026-09-19.

Current frozen-corpus analysis: [A corpus coverage](a-corpus-coverage.md), with [full counts and input hashes](a-corpus-coverage.json) and [reproducible analysis](analyze-a-coverage.py). It profiles the existing 1,377 diagnostic states, including all provenance origins, source-connected splits, potion projection effects and sparse interactions; it does not change corpus admission.

Latest follow-up: [source compatibility, raw Act 1/2 coverage and deck completeness](source-compatibility-report.md). The projection report supersedes the earlier pre-projection snapshot for this worktree; historical evidence remains preserved in [report history](report-history.json).

The owner selected MaT1g3R/Slay-the-Spire-data for a pipeline pilot before deciding whether to process SlayTheData.7z, and approved v2 after the [initial audit](small-corpus-pilot-audit.md). Implementation lives in the isolated `codex/battle-initial-states` worktree. The current corpus is diagnostic and has no formal training admission.

## Deliverables

- [Approved schema decision and field map](schema-decision.md); [strict v2 implementation](initial_state.py).
- [Pinned source inventory](source-inventory.json) and [reproducible inventory tool](inventory-source.py).
- [Reconstruction tool](reconstruct-pilot.py), [complete combat ledger](candidate-ledger.jsonl), [canonical diagnostic states](pilot-states.jsonl), [reconstruction summary](reconstruction-report.json).
- [Runtime validator](validate-runtime.py), [predeclared runtime cases](runtime-manifest.json), [runtime evidence](runtime-report.json).
- [Schema tests](test_initial_state.py), [provenance tests](test_provenance.py), [project test results](project-tests.xml), [focused prerequisite regression results](prerequisite-tests.xml).
- [Source-compatibility audit tool](audit-source-compatibility.py), [per-run/build evidence](source-compatibility.json) and [source boundary tests](test_source_compatibility.py).
- [Potion projection tool/report](potion-projection-report.py), [machine-readable projection evidence](potion-projection-report.json), and the separated source/training fields in the canonical records.

## Reproduction

Run from this worktree with Python 3.13 and the existing installed project dependencies. The source cache and backend below are read-only dependencies in the original checkout; neither is copied or rebuilt.

```powershell
python -B projects/battle-initial-states/inventory-source.py --archive C:/Users/19091/Desktop/sts2/reference/public-run-corpus/matiger-fixed.zip --backend-root C:/Users/19091/Desktop/sts2/third_party/sts_lightspeed
python -B projects/battle-initial-states/reconstruct-pilot.py --archive C:/Users/19091/Desktop/sts2/reference/public-run-corpus/matiger-fixed.zip --backend-root C:/Users/19091/Desktop/sts2/third_party/sts_lightspeed
python -B projects/battle-initial-states/audit-source-compatibility.py --reference-root C:/Users/19091/Desktop/sts2/reference
python -m pytest projects/battle-initial-states -q --junitxml=projects/battle-initial-states/project-tests.xml
python -B projects/battle-initial-states/validate-runtime.py --backend-root C:/Users/19091/Desktop/sts2/third_party/sts_lightspeed
```

The inventory verifies source bytes; the runtime validator verifies the actual imported backend binary and pinned implementation hashes. Do not refresh fingerprints to hide an unexpected dependency change.

## File ownership

- Keep new project-specific plans, source inventories, compact manifests, rejection ledgers and reports here. Add project-local extraction/validation tools and tests only when implemented.
- Keep shared environment, model, reward and trainer implementations in the existing `sts/` packages. Call those implementations instead of copying them here.
- Reuse the existing ignored `reference/public-run-corpus/` cache by reference. Put future raw sources and bulky generated evidence under ignored `reference/battle-initial-states/`; compact tracked manifests should point to them by repository-relative path and hash.
- Preserve historical documents and artifacts in place. No empty implementation directories have been created.
- Record adopted governing changes in `docs/decisions.md` before changing `spec-v6.md`. This folder does not supersede either file.

The supplied original plan remains untouched in the relic worktree. The audit records its exact path and SHA-256.
