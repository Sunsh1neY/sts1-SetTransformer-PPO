# Third relic batch: approved special imports

Date: 2026-09-19. Worktree: `sts2-relic-state-v1`, branch `codex/relic-state-v1`.
Authority: I9 one-hot identity, I11 owner decisions, I12 execution approval.

## Result and evidence boundary

Eleven approved special relics are implemented in the diagnostic `RelicEnv`, bringing the development registry from 22 to 33 identities. The registered training pool remains 39 contents, 33 source groups, two conditions and five encounters (390 configurations). No new training admission, substantial training, learning result or generalization claim follows from this import.

The combined CPU suite passed **1117 tests, with one CUDA test deselected**, in 24.90 seconds. This includes 484 reset/step surface cases (11 relics × 44 Act 1/2 encounters), per-relic deterministic replay and model forward checks, relation gradient/permutation checks, previous relic tests, registered A-path trainer/checkpoint tests, reward and legacy interface regressions. Surface coverage is not exhaustive combat completion or all-combination certification. Evidence is also saved in `evidence/relic-third-batch-checks.json`.

## Per-relic implementation

| Relic | Public state and tested behavior |
|---|---|
| Runic Pyramid | Existing hand state; turn retention, ten-card cap, energy refresh and ethereal exhaust |
| Unceasing Top | No added field; empty-hand draw, shuffle continuation, No Draw and next-turn recovery |
| Snecko Eye | Existing costs and Confused status; seven-card draw, randomized visible hand cost, unknown non-hand effective cost, Clockwork interaction |
| Velvet Choker | Existing `cards_played_this_turn`; four energy, manual six-card mask, turn reset, Havoc autoplay limit and Double Tap replay count |
| Mutagenic Strength | Existing Strength, Lose Strength and Artifact statuses; both acquisition orders with Clockwork and end-turn expiry/interception |
| Orange Pellets | Backend attack/skill/power bits; partial progress, three-type trigger, Lose Strength removal and turn reset |
| Runic Dome | Four energy; current intent type/damage/hits hidden; move history records executed actions rather than planned moves |
| Frozen Eye | Visible zero-based draw position; predictions agree with the next draw; non-hand effective costs remain unknown |
| Bottled Flame | Exact attack instance enters the opening hand; binding follows it into discard; same-name duplicates remain distinct |
| Bottled Lightning | Exact skill instance enters the opening hand; binding follows it into exhaust |
| Bottled Tornado | Exact power instance enters the opening hand; relation disappears when the played power leaves card zones |

The three bottles coexist with distinct original instances. All eleven are checked for reproducible reset/step and A-path model encoding. Gambling Chip is deferred: the existing public router supports one choice, without a complete multi-selection/deselection/finish flow. The twelve exclusions in the owner decision record remain excluded.

## Versioned fields and architecture

`relic-state-v3` has 39 raw RELIC features:

- 33 identity one-hot columns, in registry order;
- `attack_played`, `skill_played`, `power_played` from Orange Pellets (false for other identities);
- existing `counter_applicable`, `counter_known`, `counter_value_scaled` for the six periodic counter relics.

A-path CARD width is 117. The prior known-top bit is replaced by `draw_position_known` and `draw_position / 512`. Position zero means the next draw. Unknown public positions are null with a false flag; their numeric encoding is masked zero. Headbutt uses the same representation. Legacy observation/encoding remains available and is explicitly converted at the new A-path encoder. The base public envelope is reused; the relic registry/model version and strict artifact fingerprints identify the new composite contract.

Bottled input is `{"name": "Bottled Flame", "card_index": 9}`: the index identifies a concrete entry in the supplied master-deck list, never a semantic scalar. Backend instance identity follows that original card; copies have their own identity. Public routing resolves `bottled_card` relations into RELIC→CARD links. The existing Stasis ENEMY→CARD fusion design is generalized, without encoding routing IDs into tokens. When no original card entity remains, there is no live relation. Missing/invalid indices and incompatible card types are rejected.

The policy still uses four SAB layers, width 64, four heads, FF128 and one PMA seed. Source/conditional-target actions and joint PPO are unchanged. Old checkpoints are not silently accepted under the new dimensions/fingerprints.

The initial relic array is acquisition order. This affects backend initialization, including Mutagenic Strength/Clockwork; the resulting current powers carry the information required at decision time.

## Scoped backend repairs

All behavior repairs are guarded by the diagnostic relic entry; frozen legacy paths are preserved.

1. Unceasing Top now finishes an enqueued shuffle/draw before returning player control. Previously it exposed an empty hand before the queued draw completed.
2. Velvet Choker now checks its six-card limit for normal/autoplay card queue entries. Existing purge-on-use replay handling is retained. A Havoc chain previously passed the limit and played 17 cards in the test scene.
3. Mutagenic Strength and Clockwork battle-start actions use the original prepend order in this entry. Artifact can block Lose Strength when applied or the later Strength reduction, depending on order and intervening effects.
4. Runic Dome records action IDs at the actual monster-turn execution boundary, tracks entity serials to avoid inherited history, and removes direct current-intent fields. Backend plans remain internal to simulation.
5. Diagnostic initial status cards bypass `Deck::obtainRaw`'s four-type counters: its status-card index otherwise writes beyond that array into the bottle indices. Real master decks do not normally contain these diagnostic status-card entries.

The additive patch is regenerated and checked against the locked upstream plus frozen base patch chain. Backend registry fingerprint verification passed after rebuilding.

## Source verification and remaining work

Original-game rules were narrowly checked against local `desktop-1.0.jar`, SHA256 `cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673`, using relic classes and relevant GameActionManager/AbstractCard hooks. Confidence: high for the explicitly inspected hook conditions/order; verification date 2026-09-19. Proprietary reference material stays under ignored `reference/` and is not copied into simulator source.

For Unceasing Top, the original disabled-until-turn-end flag is set during end-turn autoplay. The adapter resolves this phase before returning ordinary player control; no new public flag was added. This is a scoped decision-boundary conclusion, not a proof for unsupported mechanics.

Remaining limits include exhaustive relic combinations, complete Orange Pellets coverage over every supported debuff, bottle/Stasis recovery across all special selection/replay sequences, and whole-battle coverage for every relic/encounter. The current tests include ordinary Stasis/schema regressions but do not certify every new bottle-plus-Stasis interaction. The broader ordinary relic backlog from the full scope audit remains open. Initial-state dataset expansion and training remain downstream of completing and freezing the agreed contracts.

## Reproduce

```powershell
python scripts/regenerate-relic-state-patch.py
& scripts/build-relic-state.ps1
$env:PYTHONPATH='C:/Users/19091/Desktop/sts2-relic-state-v1/third_party/sts_lightspeed/build'
python -m pytest tests/test_relic_batch_three.py tests/test_relic_batch_two.py tests/test_relic_state.py tests/test_apath.py tests/test_apath_training.py tests/test_battle_reward_v2.py tests/test_unified_entities.py tests/test_entity_input_v3.py tests/test_entity_checkpoint.py tests/test_public_consumables.py tests/test_reward_contract.py tests/test_ironclad_dynamics.py tests/test_ironclad_selection_cards.py -k 'not cuda' -q
python scripts/check-spec-v6.py
```
