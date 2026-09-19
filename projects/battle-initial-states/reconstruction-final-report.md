# A corpus reconstruction progress report

Date: 2026-09-19. Worktree: `codex/battle-initial-states`.

The formal A admission line is `backend-validated`. `source-certified` remains an optional provenance level and is not required for admission. No B states, large archive processing or PPO training were performed.

## Current result

| Layer | Count |
|---|---:|
| Raw Act 1/2 combat rows | 2,591 |
| Source-derived occurrences | 622 |
| Source-derived canonical backbones | 585 |
| Backend-validated configured instances | 585 |
| Independent source groups with states | 136 |
| Representative complete rollouts | 64/64 terminated |
| Remaining Act 1/2 rows | 1,969 |

Act distribution is 502 Act 1 and 83 Act 2. The 585 canonical backbones are kept separate from configured field values; counters, bottle bindings and missing burning-elite flags do not create additional historical backbones.

## Validation

All 585 states passed schema validation, backend reset, public observation, Token encoding, finite Set Transformer forward and legal-action validation. The runtime diagnostic then ran 32 coverage-selected states under two development seeds each: 64/64 true terminations, zero failures and zero truncations. Project tests are **48 passed**. The formal training pool, reward, model architecture, evaluation seeds and training budget were unchanged.

## First-blocker inventory

The current Act 1/2 ledger classifies only the first dependency in each source chain. Suffix rows overlap within a source group and are not independent states.

| First blocker class | Rows | Meaning |
|---|---:|---|
| `SOURCE_REQUIRED` | 100 | A core deck/permanent card value, HP/MaxHP, relic ownership, final potion inventory, encounter, Act/Floor or unique entry boundary is not uniquely available. |
| `DERIVABLE` | 1,869 | Source backbone is present, but a parser, reducer, registry or backend closure is still pending. |
| `CONFIGURABLE` | 0 | Approved dynamic fields are configured and do not stop the chain. |
| `BACKEND_RANDOM` | 0 | Opening hand, draw order and enemy initialization are backend-random and outside identity. |

The 100 core rows are `ENTRY_ROOM_OR_MULTIPLE_COMBATS_PENDING` (32), `PERSISTENT_CARD_VALUE_MISSING:RitualDagger` (46), `EVENT_ID_OR_CHOICE_MISSING` (12) and `EVENT_TIMING_AMBIGUOUS_NONIDENTICAL` (10). No relic counter, bottle binding or burning-elite value is counted as a core blocker.

The highest-yield derivable families are `POTION_DELTA_UNHANDLED` (826 rows, 116 groups, estimated suffix release 1,486), `SOURCE_ALIAS_UNMAPPED` (454 rows, 57 groups, release 161), `BACKEND_COVERAGE_PENDING` (456 rows, 66 groups, release 453), shop/campfire (74), event (37) and other targeted cases (22). Family counts are first-blocker counts and therefore sum to 1,869.

## Potion P0 result

The reducer now derives final inventory as source-observed obtained + generated - used - discarded identities. A source-visible `Potion Belt` acquisition refreshes Ascension-based capacity on ordinary, event and shop transitions. The targeted regression verifies that an A20 run can retain three source-identified potions after acquiring the Belt.

This moved `POTION_ACCOUNTING_OVERFLOW` from 87 to 34 first-blocker rows, releasing 53 rows to their next dependency. It did not increase the admitted count: those rows then expose unresolved `Potion Belt` ownership or potion identities outside the frozen backend contract. The current potion audit reports 792 rows pending the 15-name backend potion registry and 140 rows in the capacity/Potion Belt family; it records no unresolved source inventory order as a separate blocker.

## Alias and backend audit

The current registry contains 80 cards, 15 potions and 135 relics. The 454 unresolved relic rows have no token-only alias; Blue Candle, Dead Branch, Gambling Chip, Lizard Tail, Medical Kit, Potion Belt, SacredBark, Strange Spoon and Toolbox are absent registry entries. Observed extra potion names are real identities, not aliases for the 15-name public closure. Adding them requires action/observation closure and model-contract review, so no backend contract was expanded in this pass.

## Completed reconstruction rules

- Act 1 boss rewards and recorded boss relic selections now carry into Act 2 through the inter-act boundary.
- Act 2 encounter labels and floors are mapped without substituting encounters.
- Event card/relic/potion deltas, campfire `PURGE`/`DIG`/`LIFT`, Singing Bowl no-op choices and unique upgraded-card matching are applied when source fields are explicit.
- Relic counters, configurable bottle binding and missing burning-elite flags remain labeled `CONFIGURABLE`; their constructed values are never reported as historical proof.
- Canonical potion slots preserve inventory identity without claiming original slot positions.

## Historical artifact preservation and stop decision

The previous Markdown conclusions were copied before this update and their hashes are recorded in [report-history.json](report-history.json). The current machine-readable artifacts are [coverage](act12-coverage-report.json), [blocker priority](blocker-priority.json), [derivable priority](derivable-priority.json), [potion audit](potion-blocker-audit.json), [alias audit](source-alias-audit.json), [backend coverage](backend-coverage-audit.json), [runtime report](runtime-report.json) and [backend-validated corpus](admitted-a-corpus.jsonl).

The small corpus is already suitable for A coverage analysis: it has 585 backend-validated states spanning both acts and 83 Act 2 states. Remaining work is bounded to backend/card/potion closure or genuinely ambiguous source transitions. Stop reconstruction engineering when the next item would require a new action syntax, generated-card closure, expanded information permissions or a new formal scope decision. No B design is justified by the current evidence.
