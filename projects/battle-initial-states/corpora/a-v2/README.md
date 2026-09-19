# A-v2 coverage augmentation

Status: frozen diagnostic dataset. Canonical schema: `battle-initial-state-v2`. No formal training admission.

| Measure | A-v1 | A-v2 |
|---|---:|---:|
| Total states | 1,377 | 1,715 |
| Act 2 states | 373 | 630 |
| Act 2 entry HP at or below 25% | 4 | 142 |
| Audit train states | 1,044 | 1,240 |
| Audit dev states | 199 | 288 |
| Audit holdout states | 134 | 187 |

The 338 additions comprise 138 low-HP states, 164 counter variants and 36 controlled card-combination states. Baseline records are unchanged. Independent historical source coverage has not increased.

## Rare combination definitions

Each exact combination below has three new examples from distinct parent components in each of train, dev and holdout, for nine examples per combination. These narrower exact combinations differ from the broader OR-based probes in the original coverage report; their zero baseline counts must not be confused with that report's broader nonzero counts.

- Barricade + Body Slam + Entrench.
- Rupture + Hemokinesis.
- Inflame + Heavy Blade + Limit Break.
- Dropkick + Thunderclap.

Missing cards are appended at upgrade zero; existing deck contents and relics are retained. This establishes controlled co-occurrence coverage, not successful combo execution, natural run reachability, or SAB generalization.

## Entry-counter coverage

- Pen Nib, Nunchaku and Ink Bottle: all values 0 through 9.
- Happy Flower and Sundial: all values 0 through 2.
- Incense Burner: all values 0 through 5.

Only existing owned instances are varied. No relic identities are added, no unknown state is guessed, and no randomization is applied to other relics. See `generation-policy.json` for parent selection and scope.

## Validation

All 338 additions passed reset, token encoding, model forward and one legal action through the existing backend. A selected 32-state subset across two development seeds completed 64 episodes, all terminated, with zero failures. The untrained model's 11 victories and 53 defeats are runtime diagnostics, not evidence of learning or a comparison against A-v1.

Baseline runtime evidence is inherited from A-v1; the 1,715-state combined file was not separately rerun in full. Lineage, canonical hashes, exact baseline inclusion and zero connected-component leakage across partitions were checked. Full evidence is in `validation/coverage-and-integrity.json` and `validation/runtime-report.json`.

Verify frozen bytes using the project-level `version-corpora.py verify` command. Future changes require another version. Burning elites, large-corpus work and the SAB generalization dataset remain deferred.
