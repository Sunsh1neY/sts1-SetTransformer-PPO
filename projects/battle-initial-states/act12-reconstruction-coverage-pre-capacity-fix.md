# Act 1/2 reconstruction coverage under the backend-validated A standard

Date: 2026-09-19. Status: current working result after configurable-state relaxation.

The A admission line is `backend-validated`. A source-certified build/recorder/ruleset proof is retained as provenance metadata but is not required for corpus admission. Configured counter, burning-elite and bottle-binding values are reported separately from the source backbone.

## Current counts

| Layer | Count |
|---|---:|
| Raw Act 1/2 combat rows | 2,591 |
| Rule-derived occurrences | 595 |
| Source-derived canonical backbones | 558 |
| Backend-validated configured instances | 558 |
| Representative complete-rollout instances | 32 |
| Remaining combat rows | 1,996 |

All 558 instances passed schema adaptation, backend reset, public observation, Token encoding, finite Set Transformer forward, legal joint-action validation and deterministic one-step checks. The 32 coverage-selected instances ran two development seeds each: 64/64 true terminations, zero exceptions and zero truncations. The formal A-path training pool remains unchanged; this project corpus is admitted as `backend-validated` but is not silently inserted into that pool.

The 558 source backbones are not inflated by configured values. A configured counter, bottle binding or burning flag does not create a new historical backbone. Their source ownership remains real-run-derived; the configured field carries `origin=configured` in the reconstruction evidence.

## Why 2,040 rows are still absent

The blocker ledger selects the first dependency in each combat's source chain and preserves all later detected blockers. Under the four requested categories:

| First blocker class | Combat rows | Source groups | Meaning |
|---|---:|---:|---|
| `SOURCE_REQUIRED` | 78 | 25 | A core Deck/HP/MaxHP/ownership/potion/encounter/entry field is not uniquely available, or a permanent card-instance state cannot be legally represented. |
| `DERIVABLE` | 1,918 | 153 | The source backbone is present, but the current parser, event/shop transition rules, Neow parser, potion registry or backend content registry has not yet consumed it. |
| `CONFIGURABLE` | 0 | 0 | Dynamic fields are now configured in the candidate instead of stopping the prefix. |
| `BACKEND_RANDOM` | 0 | 0 | Backend-resampled hidden draw/order state is intentionally outside initial-state identity and does not block reset. |

The 76 core rows are:

| First core reason | Rows | Groups |
|---|---:|---:|
| `PERSISTENT_CARD_VALUE_MISSING:RitualDagger` | 34 | 7 |
| `ENTRY_ROOM_OR_MULTIPLE_COMBATS_PENDING` | 27 | 25 |
| `EVENT_ID_OR_CHOICE_MISSING` | 12 | 2 |
| `EVENT_TIMING_AMBIGUOUS_NONIDENTICAL` | 5 | 2 |

`POTION_ACCOUNTING_OVERFLOW` is currently classified as `DERIVABLE`, because the observed inventory is present but the current capacity/backend path does not yet consume every source potion identity. It is not counted as a missing potion backbone. This classification will be revisited only if the source inventory itself cannot be uniquely calculated.

The largest derivable families are unsupported or choice potion identities, unhandled Neow reward forms, event/shop/card transition coverage and parser aliases. Their rows are not historical A failures: the raw source contains enough backbone information for a targeted implementation pass, but the current adapter has not yet converted all of it.

## Coverage shape

The validated instances contain 495 Act 1 and 63 Act 2 backbones. Act 2 reaches floors 18, 19, 20, 21, 22, 23, 25, 27, 28, 29, 30, 31 and 33 in this pass. Encounter coverage includes Act 2 `SLIME_BOSS`, `THE_GUARDIAN`, `HEXAGHOST`, `SPHERIC_GUARDIAN`, `CHOSEN`, `SHELL_PARASITE`, `SNAKE_PLANT`, `THREE_BYRDS`, `CHOSEN_AND_BYRDS`, `GREMLIN_LEADER`, `SLAVERS` and `BOOK_OF_STABBING`, in addition to the Act 1 set. Elite burning is configured false for backend validation where the source lacks the flag; this is not historical evidence that the run was non-burning.

The machine-readable semantic distribution is in [act12-coverage-report.json](act12-coverage-report.json). The per-combat first-blocker ledger and priority estimates are [act12-blocker-ledger.jsonl](act12-blocker-ledger.jsonl) and [blocker-priority.json](blocker-priority.json). The admitted configured corpus is [admitted-a-corpus.jsonl](admitted-a-corpus.jsonl), with its admission summary in [a-corpus-admission.json](a-corpus-admission.json).

## Interpretation and next work

The small corpus is already useful as a backend-validated A corpus under the current definition: 558 states cover both acts and many encounter/relic/potion combinations. It is not yet broad enough to freeze the final training distribution because Act 2 and several card/potion families remain sparse.

The next engineering priority is the high-yield `DERIVABLE` set, in this order:

1. accept the remaining explicit potion identities through the current registry or a documented configurable potion path;
2. implement the two Neow reward forms whose logs already contain the selected relic and numeric effects;
3. extend event/shop generic delta application for rows whose card/relic/potion lists are explicit;
4. resolve aliases and current backend support for remaining observed cards/relics;
5. separately handle the 78 `SOURCE_REQUIRED` rows, beginning with same-floor entry ambiguity and Ritual Dagger instance values.

No B state was generated, no large archive was processed, and no PPO training was launched. `source-certified` remains an optional stronger provenance label rather than the A admission gate.
