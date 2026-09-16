# Setup and validation

Status: existing project commands, consolidated on 2026-09-16. This page has not been validated in a fresh clone. The active contract is [spec-v6](../spec-v6.md); supported local engineering evidence is in the [A-path integration report](a-path-main-integration-report.md).

## Supported build route

The recorded local stack is Windows, MSYS2 mingw64 and Python 3.13. Use the same Python interpreter for building and running. In MSYS2, install the toolchain:

```bash
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja
```

Then, from the repository root in PowerShell:

```powershell
python -m pip install -e ".[dev]"
./scripts/build-enemy-potion.ps1 -Python python -Jobs 1
```

The integrated build script uses the [backend lock](../scripts/lightspeed-lock.json), base patch and enemy integration patch. A Python checkout or base-only backend build is insufficient. Existing source conflicts must be inspected rather than overwritten. Do not copy relocated build caches and assume they remain usable.

## Bounded checks

After preparing the backend, the current A-path model and training/recovery tests are:

```powershell
python -m pytest -q tests/test_apath.py tests/test_apath_training.py -k "not cuda"
```

These tests include short PPO updates; they are engineering checks, not a substantive training experiment. Document/specification checks can be run without starting training:

```powershell
python scripts/check-spec-v6.py
```

For a separately needed full regression, with required local fixtures available:

```powershell
python -m pytest -q --ignore=tests/test_enemy_status_export.py -k "not cuda"
python -m pytest -q tests/test_enemy_status_export.py
```

The second command is the independent C++ status fixture. GPU verification requires the matching CUDA interpreter. Missing backend/data, skips and failures must be reported separately; they are not successful validation.

## Training and diagnostics

The current training entry is [run-a-path-ppo.py](../scripts/run-a-path-ppo.py). Inspect `--help` before planning a run. Actual training needs an explicit scope, output directory and bounded budget; an earlier four-hour authorization is not automatically renewed.

For separately authorized broad environment diagnostics, the existing script is:

```powershell
python scripts/diagnose-enemy-full-card.py --act12 --output reference/act12-local-diagnostic.json
```

The output must not already exist. This is a 6,600-case diagnostic route, not a quick-start requirement or training admission. `IroncladEnv.reset(..., diagnostic=True)` and the registered `APathEnv` training entry have different admission semantics.

## Reproduction limits

A clone does not include ignored runs, checkpoints, most reference fixtures, or third-party builds. Existing reports document outcomes on their original stack; clean-clone evaluation and report regeneration still need verification and an accessible artifact package. No `scripts/reproduce.py` interface is claimed to exist.

Use the [artifact inventory](repository-inventory.md) and [desktop recovery instructions](desktop-repo-cleanup-2026-09-14.md). Preserve source/backend/task fingerprints and old seed identities. The cleanup only moves document paths used by legacy source archivers; original ZIPs, manifests and checkpoints remain untouched.
