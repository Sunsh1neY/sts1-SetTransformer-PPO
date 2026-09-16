# Repository cleanup report

Date: 2026-09-16. Baseline: local main at `de951cd`. Scope: owner-approved decision I6, documentation/navigation cleanup plus the explicitly approved historical-specification path repair. Authority remains [spec-v6](../spec-v6.md).

## Changes

- English README, one-page research overview, setup guide and documentation map now introduce the fixed-pool A-path learning question. The earlier MLP/Set study is a short historical summary with its inconclusive difference and limitations.
- Eighteen obsolete specifications, prompts and research documents were moved to `archive/`, including root v4/v5 and the old learning guide. The archive index and migration manifest record original paths, source/result hashes and original checkout line endings. Original README/AGENTS snapshots remain byte-identical; changed historical document bodies only have link rebasing and line-ending normalization.
- Existing phase plans kept at stable paths have explicit historical notices. The `a-path/` design/fixture package is unchanged to preserve its source manifest; its historical role is documented in the navigation map.
- The prepared relic plan is preserved as a pending source. Relics and Act 1/2 combat fidelity remain next-stage work rather than obsolete or already implemented claims.
- Root AGENTS and decision I6 resolve the English-language policy and immediate research objective. The active specification carries a dated reading note and amendment; reward, schedule, Gate and budget rules remain intact.
- Legacy PPO/MLP/S5 snapshot utilities use explicit `archive/spec-v4.md` and `archive/spec-v5.md` paths. Current v6 is required in the legacy PPO snapshot. The existing archive/recovery test also verifies ZIP entries and content hashes.

## Validation

| Check | Result |
|---|---|
| `python -m pytest -q tests/test_ppo_training.py tests/test_apath.py tests/test_apath_training.py -k "not cuda"` | 41 passed, 1 CUDA test deselected, 22.25 seconds |
| MLP `snapshot_sources()` on the real working tree, writing only a temporary output | Passed; ZIP integrity, archived specification contents and manifest hashes matched |
| S5 freeze script's explicit root/document file list | Passed static path-existence check; full historical S5 bundle was not rebuilt |
| Changed Python files | Syntax compilation passed; after final archive normalization the metadata/recovery test and MLP ZIP check passed again |
| Specification and navigation checks | Passed; 315 local links across 44 changed/curated documents checked, with no broken targets. See [verification record](repository-cleanup-checks.json). An intermediate check flagged this report before it was written |
| Preservation | 80 protected runtime/config/patch/seed/design-package files and two pre-existing untracked documents matched pre-edit hashes; all 21 migration entries and nine representative artifact hashes verified |

The short tests include actual PPO updates and recovery checks; they are engineering validation, not new substantive training. No full CPU regression, CUDA rerun, backend rebuild, clean-clone reproduction, historical checkpoint revalidation, or statistical recomputation is claimed.

## Remaining work

The first-pass navigation objective and final checks are complete. Next work is tracked in [pending plans](plans/README.md) and the [inventory](repository-inventory.md): establish relic/Act 1–2 acceptance boundaries, audit original A-path run evidence, and verify an accessible reproduction route. Complete English translation remains incremental. No remote push or publication is performed.

The two original untracked drafts remain outside the cleanup commit. The local cleanup commit is identifiable by subject `Clarify research entry points and archive historical plans`; its hash is reported in the delivery message rather than embedded in the commit itself.
