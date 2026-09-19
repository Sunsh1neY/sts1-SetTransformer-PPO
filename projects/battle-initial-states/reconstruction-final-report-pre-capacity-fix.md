# A corpus reconstruction progress report

Date: 2026-09-19. Worktree: `codex/battle-initial-states`.

The current A admission standard is `backend-validated`. Source certification remains provenance metadata and is not required for admission. No B states, large archive processing or PPO training were performed.

## Current result

| Layer | Count |
|---|---:|
| Raw Act 1/2 combat rows | 2,591 |
| Source-derived occurrences | 622 |
| Source-derived canonical backbones | 585 |
| Backend-validated configured instances | 585 |
| Representative complete rollouts | 64/64 terminated |
| Remaining battle rows | 1,969 |

The latest re-run after the event/campfire and card-instance reducer edits is 585 canonical states. The current machine-readable runtime report records 585/585 one-step checks and 64/64 representative complete terminations.

The source backbone count is kept separate from configured values. Relic counters, bottle bindings and missing burning-elite flags do not create additional historical backbones. They are instantiated with a legal configured value and carry configured provenance.

## Validation

The current runtime validator checks schema adaptation, backend reset, public observation, Token encoding, finite Set Transformer forward, normalized joint probabilities and legal action routing for every admitted instance. It also runs 32 coverage-selected states under two development seeds each. Re-run `validate-runtime.py` after any corpus regeneration before using `admitted-a-corpus.jsonl` as the current admission artifact.

Project tests remain **47 passed**. The formal training pool, reward, model architecture, evaluation seeds and training budget were not changed.

## Blocker interpretation

The current ledger uses four classes:

| Class | Current role |
|---|---|
| `SOURCE_REQUIRED` | Only a missing core Deck, permanent card-instance value, HP/MaxHP, relic ownership, final potion inventory, encounter, Act/Floor or unique entry boundary stops the source backbone. |
| `CONFIGURABLE` | Counter values, bottle binding and burning elite are legal configured fields; they do not stop the run chain. |
| `DERIVABLE` | Parser, normalized event, shop/campfire, potion registry or backend coverage remains to be consumed. |
| `BACKEND_RANDOM` | Opening hand, draw order and enemy random realization are generated from the independent backend seed. |

The current inventory has 95 `SOURCE_REQUIRED` rows and 1,874 `DERIVABLE` rows. These are first-blocker row counts; suffix rows overlap across one source group's blocked prefix and are not independent states.

The persistent-card blocker remains genuine: Ritual Dagger values are not recoverable from the inspected source at the required entry time and are not silently configured. Same-floor multiple-combat entries and non-equivalent duplicate event records remain genuine source-boundary blockers. Missing relic counters, bottle relation and burning elite are not in this category.

## Completed general rules

- Act 1 boss transition now applies the source-selected boss reward card and boss relic, then crosses the recorded inter-act boundary into Act 2.
- Act 2 encounter labels and floors through the available source history are mapped to the current expansion contract without replacing encounters.
- Neow `BOSS_RELIC` and `THREE_ENEMY_KILL` forms consume the recorded selected relic instead of failing the initial parser.
- Current relic registry names and source aliases are normalized; persistent counters use a legal configured value when historical values are not required for backbone identity. Bottle bindings use a source binding when it is type-valid, otherwise a legal deck target; source/configured origin is retained.
- Missing burning-elite flags configure `false` for backend validation and are never reported as historical proof.
- Potion reducer uses obtained, generated, used and discarded identities to derive the next inventory multiset; canonical slot order remains separate from historical slot provenance.
- Event rows consume explicit card/relic/potion deltas; same-floor card choices are applied when the selected result is recorded. Campfire `PURGE`, `DIG` and `LIFT` no longer stop the persistent reducer; upgraded source card IDs match a unique upgraded instance only.
- `Singing Bowl` is consumed as a no-Deck-delta choice.

## Current P0 coverage limits

The remaining high-volume derivable families are:

- backend potion registry coverage: source potion identities are known, but the frozen public closure currently accepts 15 potion names;
- backend/card closure: observed colorless, curse and special generated cards are outside the current 80-card Ironclad expanded registry;
- unresolved relics absent from the current 135-entry registry: Blue Candle, Dead Branch, Gambling Chip, Lizard Tail, Medical Kit, Potion Belt, SacredBark, Strange Spoon and Toolbox;
- potion capacity paths involving Potion Belt and overflow inventory;
- event/shop deltas with genuinely ambiguous card instance or same-floor selection semantics.

These are backend/parser coverage decisions, not evidence that the original run backbone is absent. The machine-readable reports are:

- [coverage](act12-coverage-report.json)
- [blocker priority](blocker-priority.json)
- [derivable priority](derivable-priority.json)
- [potion blocker audit](potion-blocker-audit.json)
- [alias audit](source-alias-audit.json)
- [backend coverage audit](backend-coverage-audit.json)
- [backend-validated corpus](admitted-a-corpus.jsonl)

## Stop decision

The corpus is already suitable for a first A-path coverage analysis because it contains hundreds of backend-validated Act 1/2 states and a small but real Act 2 slice. Reconstruction engineering should continue only for the high-yield backend/parser items above. It should stop when those items require new action syntax, generated-card closure, expanded information permissions, or a new formal scope decision. No B design is justified yet; first finish the bounded P0 audit and then freeze the A coverage report before making a training-distribution decision.
