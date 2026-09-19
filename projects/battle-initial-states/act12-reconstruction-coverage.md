# Act 1/2 reconstruction coverage under the backend-validated A standard

Date: 2026-09-19. This report supersedes the prior 585-state pre-projection snapshot; earlier evidence is preserved in [report-history.json](report-history.json).

`backend-validated` is the A admission line. Source build/recorder/ruleset evidence remains provenance metadata. Configured counters, burning-elite values and bottle bindings are separate from source-derived backbone identity.

## Current counts

| Layer | Count |
|---|---:|
| Raw Act 1/2 combat rows | 2,591 |
| Source-derived occurrences | 2,330 |
| Canonical source backbones | 2,292 |
| Scope-projected occurrences | 1,406 |
| Backend-validated occurrences | 1,414 |
| Backend-validated configured instances | 1,377 |
| Independent source groups with states | 141 |
| Representative complete-rollout cases | 64/64 terminated |
| Remaining combat rows | 1,177 |

The canonical validated distribution is 1,004 Act 1 and 373 Act 2 instances. All 1,377 states passed schema, reset, observation, Token, forward and legal-action checks; the rollout diagnostic recorded zero failures and zero truncations. The formal A-path training pool remains unchanged.

## First blockers

| Class | Rows | Source groups | Interpretation |
|---|---:|---:|---|
| `SOURCE_REQUIRED` | 146 | first blocker | Core deck/permanent state, HP/MaxHP, ownership, final inventory, encounter/floor or unique entry boundary cannot be determined. |
| `RECONSTRUCTION_PENDING` | 115 | first blocker | Source/parser/reducer evidence still needs a rule or a lossless field. |
| `BACKEND_SCOPE_PENDING` | 916 | first blocker | Source backbone is known, but card/relic/backend combat closure remains pending. |
| `SCOPE_PROJECTABLE` | 1,406 | transformation count; overlaps | Unsupported source potions were removed only in the training instance. |
| `CONFIGURABLE` | 701 | transformation count; overlaps | Approved dynamic values are represented with configured provenance. |
| `BACKEND_RANDOM` | 0 | 0 | Backend-sampled hidden battle state does not define initial-state identity. |

Core remaining reasons include 146 source-required rows, 115 reconstruction-pending rows and 916 backend-scope rows. Scope-projectable and configurable counts are intentionally separate overlapping transformations, not additional first-blocker rows.

## Potion and registry findings

The source logger exposes `potions_obtained`, generated potion arrays, per-floor use and discard arrays. The reducer uses their final multiset and does not require replaying an unrecorded UI order. `supported-potions-only-v1` now projects 1,406 source occurrences; 792 rows are released because unsupported potion was their only non-configurable backend blocker. Act 1 contributes 502 released rows and Act 2 contributes 290. Potion Belt remains source-preserved and backend-scope-pending; it is not removed by potion projection.

No pure source relic aliases remain. The current closure is 80 cards, 15 potions and 135 relics. Extending that closure requires backend action/observation semantics and is outside this bounded reconstruction pass.

## Decision

Unsupported potion projection is complete and the corpus is ready for the next explicitly bounded A coverage analysis. Do not generate B states, download the large archive or start PPO training in this pass.
