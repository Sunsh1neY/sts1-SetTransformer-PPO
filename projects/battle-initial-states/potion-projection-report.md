# Supported-potion scope projection

Date: 2026-09-19. Policy: `supported-potions-only-v1`.

This is a project-corpus change only. The formal A-path training pool, reward,
model, evaluation seeds and backend registry were not changed.

## Result

The source reconstruction and training-instance layers are now separate:

| Layer | Count |
|---|---:|
| Act 1/2 source-derived occurrences | 2,330 |
| Canonical source backbones | 2,292 |
| Scope-projected occurrences | 1,406 |
| Scope-projected instances | 1,406 |
| Configured occurrences | 701 |
| Backend-validated occurrences | 1,414 |
| Backend-validated canonical instances | 1,377 |

The previous pre-projection baseline was 622 backend-validated occurrences and
585 canonical instances. Of the 1,406 rows that had an unsupported potion
blocker, 792 had no other non-configurable backend blocker and were released by
the projection: Act 1 contributed 502 and Act 2 contributed 290.

The projected corpus passed 1,377/1,377 reset, observation, Token, model
forward and legal-action checks. The bounded complete-combat diagnostic passed
64/64 true terminations with zero failures and zero truncations. These are
engineering/runtime results, not a learning or generalization claim.

## Projection semantics

For a source inventory such as `[Weak Potion, PowerPotion]`, the stored layers
are:

```text
source backbone:       [Weak Potion, PowerPotion]
training instance:     [Weak Potion, empty]
```

The source backbone retains the complete source inventory and its provenance.
The training instance removes only identities outside the current 15-potion
backend whitelist, preserves list capacity, never substitutes another potion,
and records every removed identity. No backend potion registry or action space
was expanded.

Removed source identities were:

`AttackPotion`, `BlessingOfTheForge`, `BloodPotion`, `ColorlessPotion`,
`CultistPotion`, `DistilledChaos`, `DuplicationPotion`, `ElixirPotion`,
`EntropicBrew`, `FairyPotion`, `Fire Potion`, `GamblersBrew`,
`LiquidMemories`, `PowerPotion`, `SkillPotion`, `SmokeBomb`, `SneckoOil`,
and `SteroidPotion`.

Potion Belt was not removed. It is a combat-relevant relic and remains a
backend-scope blocker where the current relic registry cannot represent it.
Unsupported cards and the other unresolved combat-relevant relics were also
not projected away.

## Current layer diagnostics

For Act 1/2 first-blocker rows after the projection, the mutually exclusive
remaining first-blocker counts are:

| Category | Rows |
|---|---:|
| `SOURCE_REQUIRED` | 146 |
| `RECONSTRUCTION_PENDING` | 115 |
| `BACKEND_SCOPE_PENDING` | 916 |
| backend-validated (`NONE`) | 1,414 |

The following are transformation/field counts and intentionally overlap the
first-blocker table: `SCOPE_PROJECTABLE` 1,406, `CONFIGURABLE` 701, and
`BACKEND_RANDOM` 0.

Machine-readable evidence is in
[`potion-projection-report.json`](potion-projection-report.json), with the
canonical records in [`pilot-states.jsonl`](pilot-states.jsonl), the complete
source ledger in [`candidate-ledger.jsonl`](candidate-ledger.jsonl), and the
runtime result in [`runtime-report.json`](runtime-report.json).
