# Remaining Act 1/2 relic import report

Date: 2026-09-19. Baseline: `58448c7`. Owner decision: I13.

## Delivered scope

135 diagnostic relic identities: 33 previously imported plus all 102 eligible remaining entries (56 combat entries and 46 run/acquisition ownership entries). Twelve owner exclusions and deferred Gambling Chip remain excluded. The historical 148-entry scope audit is unchanged.

The 46 ownership entries consume explicitly configured post-acquisition deck, HP, gold and potion inventory. Their acquisition, chest, shop, campfire, map and reward-screen operations are not implemented by this work. Destination combat-room entry is still processed where relevant: active Maw Bank awards 12 gold, Ectoplasm blocks it, and Bloody Idol heals on successful gold gain. An inactive Maw Bank is not inferred from ownership.

## Public state contract

`relic-state-v4`: 135 one-hot identity fields + 3 Orange Pellets progress bits + 3 counter fields = **141 raw RELIC features**. CARD remains 117. The four-SAB/64-width/four-head/FF128/single-PMA backbone and joint source-target PPO design are unchanged. The new model identity is `a-path-four-sab-pma-pointer-relic-v4`; previous fingerprinted checkpoints remain incompatible rather than silently migrated.

| Relic | Required pre-combat input | Decision-time semantics |
|---|---|---|
| Ancient Tea Set | `{"name":"Ancient Tea Set","counter":0 or 1}` | Explicit rest-ready flag; consumed once on opening turn. |
| Girya | Counter 0..3 | Actual persistent lifts; never inferred from ownership. |
| Neow's Lament | Counter 0..3 | Remaining combats; consumed at initialization, never twice at exit. |
| Omamori | Counter 0..2 | Explicit charges preserved; curse-acquisition execution is outside the supported Act 1/2 battle surface. |
| Maw Bank | Counter 0 or 1 | Active flag for destination-room gold; no shop execution. |
| Centennial Puzzle | Name string | Pre-battle reset guarantees unused; actual backend consumption becomes a public 0/1 flag. |

Du-Vu Doll derives its opening Strength from the supplied master deck's actual curse cards. Akabeko/Helix/Clay use existing Vigor/Buffer/Next Turn Block powers. Kunai/Shuriken/Fan/Letter Opener/Art of War/Pocketwatch use existing public per-turn card counts; timed relics use the existing public turn. No hidden RNG, routing slot, or invented history is introduced.

## Mechanism repairs

All changed behavior is gated to the relic diagnostic entry, retaining the frozen legacy paths.

- Buffer now intercepts positive direct HP loss before Tungsten Rod's final reduction.
- Toy Ornithopter now schedules its missing five-HP heal when a potion is used.
- Face of Cleric now updates maximum HP and healing on victory.
- Gremlin Visage queues its Weak application with the correct non-monster source, allowing Clockwork Souvenir's Artifact to resolve first and Weak to expire after the first player turn.
- Neow's Lament no longer gives HP to uninitialized summon placeholders; its remaining count is consumed at battle entry rather than exit.
- Ancient Tea Set uses supplied readiness instead of the last-room shortcut.
- Red Skull removes three Strength when healing crosses above half HP; the previous backend passed the wrong sign.
- Magic Flower rounds positive odd healing amounts correctly (five becomes eight, not seven).

The additive patch generator now includes the modified Player header/source in addition to the adapter and BattleContext files. It checks reproduction against the locked backend plus frozen base patch chain.

## Validation and evidence boundaries

Final validation: **5,865 passed, zero failures/errors, one CUDA test deselected**. The final full suite completed in approximately 102 seconds. Machine-readable hashes/results are in `docs/evidence/relic-remaining-checks.json`; the complete test case log is in `docs/evidence/relic-remaining-tests.xml`. Backend rebuild/fingerprint verification, additive patch reproduction and spec consistency checks passed.

Tests distinguish targeted trigger/state/counter checks, ownership preservation, deterministic replay, model forward passes, and the 102-by-44 Act 1/2 reset/step surface. One-step encounter coverage is not complete-episode certification or proof of all relic combinations. The fixed training pool, evaluation seeds, reward v2 and training budget are unchanged. No training, learning-improvement claim, dataset admission, merge or push is included.

Original-game hook conditions were checked through local reference classes from `desktop-1.0.jar`, SHA256 `cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673`. Confidence: high for explicitly inspected hook conditions; verification date: 2026-09-19. Proprietary reference code remains ignored and was not copied into simulator source. This is scoped simulation evidence, not exhaustive original-game parity. Act 3 mechanisms and arbitrary unsupported initial card types remain outside scope.

## Per-entry manifest

Each row below has an independent reset/step surface and model/replay check. Ownership-only rows additionally have a configured-state/terminal-preservation test. Targeted combat checks are in `tests/test_relic_remaining.py`.

| Relic | Backend identity | Scope | Counter |
|---|---|---|---|
| The Abacus | `THE_ABACUS` | combat_mechanism | Existing public powers/counts or no battle progress |
| Akabeko | `AKABEKO` | combat_mechanism | Existing public powers/counts or no battle progress |
| Strike Dummy | `STRIKE_DUMMY` | combat_mechanism | Existing public powers/counts or no battle progress |
| Brimstone | `BRIMSTONE` | combat_mechanism | Existing public powers/counts or no battle progress |
| Captain's Wheel | `CAPTAINS_WHEEL` | combat_mechanism | Existing public powers/counts or no battle progress |
| Horn Cleat | `HORN_CLEAT` | combat_mechanism | Existing public powers/counts or no battle progress |
| Mercury Hourglass | `MERCURY_HOURGLASS` | combat_mechanism | Existing public powers/counts or no battle progress |
| Sling of Courage | `SLING_OF_COURAGE` | combat_mechanism | Existing public powers/counts or no battle progress |
| Thread and Needle | `THREAD_AND_NEEDLE` | combat_mechanism | Existing public powers/counts or no battle progress |
| Pantograph | `PANTOGRAPH` | combat_mechanism | Existing public powers/counts or no battle progress |
| Busted Crown | `BUSTED_CROWN` | combat_mechanism | Existing public powers/counts or no battle progress |
| Coffee Dripper | `COFFEE_DRIPPER` | combat_mechanism | Existing public powers/counts or no battle progress |
| Cursed Key | `CURSED_KEY` | combat_mechanism | Existing public powers/counts or no battle progress |
| Fusion Hammer | `FUSION_HAMMER` | combat_mechanism | Existing public powers/counts or no battle progress |
| Philosopher's Stone | `PHILOSOPHERS_STONE` | combat_mechanism | Existing public powers/counts or no battle progress |
| Mark of Pain | `MARK_OF_PAIN` | combat_mechanism | Existing public powers/counts or no battle progress |
| The Boot | `THE_BOOT` | combat_mechanism | Existing public powers/counts or no battle progress |
| Paper Phrog | `PAPER_PHROG` | combat_mechanism | Existing public powers/counts or no battle progress |
| Calipers | `CALIPERS` | combat_mechanism | Existing public powers/counts or no battle progress |
| Ice Cream | `ICE_CREAM` | combat_mechanism | Existing public powers/counts or no battle progress |
| Bird-Faced Urn | `BIRD_FACED_URN` | combat_mechanism | Existing public powers/counts or no battle progress |
| Charon's Ashes | `CHARONS_ASHES` | combat_mechanism | Existing public powers/counts or no battle progress |
| Chemical X | `CHEMICAL_X` | combat_mechanism | Existing public powers/counts or no battle progress |
| Tungsten Rod | `TUNGSTEN_ROD` | combat_mechanism | Existing public powers/counts or no battle progress |
| Torii | `TORII` | combat_mechanism | Existing public powers/counts or no battle progress |
| Fossilized Helix | `FOSSILIZED_HELIX` | combat_mechanism | Existing public powers/counts or no battle progress |
| Art of War | `ART_OF_WAR` | combat_mechanism | Existing public powers/counts or no battle progress |
| Self-Forming Clay | `SELF_FORMING_CLAY` | combat_mechanism | Existing public powers/counts or no battle progress |
| Runic Cube | `RUNIC_CUBE` | combat_mechanism | Existing public powers/counts or no battle progress |
| Red Skull | `RED_SKULL` | combat_mechanism | Existing public powers/counts or no battle progress |
| Kunai | `KUNAI` | combat_mechanism | Existing public powers/counts or no battle progress |
| Shuriken | `SHURIKEN` | combat_mechanism | Existing public powers/counts or no battle progress |
| Ornamental Fan | `ORNAMENTAL_FAN` | combat_mechanism | Existing public powers/counts or no battle progress |
| Letter Opener | `LETTER_OPENER` | combat_mechanism | Existing public powers/counts or no battle progress |
| Pocketwatch | `POCKETWATCH` | combat_mechanism | Existing public powers/counts or no battle progress |
| Stone Calendar | `STONE_CALENDAR` | combat_mechanism | Existing public powers/counts or no battle progress |
| Gremlin Horn | `GREMLIN_HORN` | combat_mechanism | Existing public powers/counts or no battle progress |
| Magic Flower | `MAGIC_FLOWER` | combat_mechanism | Existing public powers/counts or no battle progress |
| Toy Ornithopter | `TOY_ORNITHOPTER` | combat_mechanism | Existing public powers/counts or no battle progress |
| Ginger | `GINGER` | combat_mechanism | Existing public powers/counts or no battle progress |
| Turnip | `TURNIP` | combat_mechanism | Existing public powers/counts or no battle progress |
| Odd Mushroom | `ODD_MUSHROOM` | combat_mechanism | Existing public powers/counts or no battle progress |
| Champion's Belt | `CHAMPION_BELT` | combat_mechanism | Existing public powers/counts or no battle progress |
| Hand Drill | `HAND_DRILL` | combat_mechanism | Existing public powers/counts or no battle progress |
| Mummified Hand | `MUMMIFIED_HAND` | combat_mechanism | Existing public powers/counts or no battle progress |
| Warped Tongs | `WARPED_TONGS` | combat_mechanism | Existing public powers/counts or no battle progress |
| Sozu | `SOZU` | combat_mechanism | Existing public powers/counts or no battle progress |
| Ectoplasm | `ECTOPLASM` | combat_mechanism | Existing public powers/counts or no battle progress |
| Gremlin Visage | `GREMLIN_VISAGE` | combat_mechanism | Existing public powers/counts or no battle progress |
| Face of Cleric | `FACE_OF_CLERIC` | combat_mechanism | Existing public powers/counts or no battle progress |
| Bloody Idol | `BLOODY_IDOL` | combat_mechanism | Existing public powers/counts or no battle progress |
| Neow's Lament | `NEOWS_LAMENT` | combat_mechanism | remaining_combats: 0..3 |
| Girya | `GIRYA` | combat_mechanism | lifts: 0..3 |
| Ancient Tea Set | `ANCIENT_TEA_SET` | combat_mechanism | ready_after_rest: 0..1 |
| Centennial Puzzle | `CENTENNIAL_PUZZLE` | combat_mechanism | used_this_combat: 0..1 |
| Du-Vu Doll | `DU_VU_DOLL` | combat_mechanism | Existing public powers/counts or no battle progress |
| Astrolabe | `ASTROLABE` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Black Star | `BLACK_STAR` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Calling Bell | `CALLING_BELL` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Cauldron | `CAULDRON` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Ceramic Fish | `CERAMIC_FISH` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| The Courier | `THE_COURIER` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Cultist Headpiece | `CULTIST_HEADPIECE` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Darkstone Periapt | `DARKSTONE_PERIAPT` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Dollys Mirror | `DOLLYS_MIRROR` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Dream Catcher | `DREAM_CATCHER` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Empty Cage | `EMPTY_CAGE` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Eternal Feather | `ETERNAL_FEATHER` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Frozen Egg | `FROZEN_EGG` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Golden Idol | `GOLDEN_IDOL` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Juzu Bracelet | `JUZU_BRACELET` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Mango | `MANGO` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Matryoshka | `MATRYOSHKA` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Maw Bank | `MAW_BANK` | ownership_and_applicable_room_entry_hook | active: 0..1 |
| Meal Ticket | `MEAL_TICKET` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Membership Card | `MEMBERSHIP_CARD` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Molten Egg | `MOLTEN_EGG` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Nloths Gift | `NLOTHS_GIFT` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Nloths Hungry Face | `NLOTHS_HUNGRY_FACE` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Old Coin | `OLD_COIN` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Omamori | `OMAMORI` | ownership_and_applicable_room_entry_hook | remaining_charges: 0..2 |
| Orrery | `ORRERY` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Pandoras Box | `PANDORAS_BOX` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Peace Pipe | `PEACE_PIPE` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Pear | `PEAR` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Prayer Wheel | `PRAYER_WHEEL` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Question Card | `QUESTION_CARD` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Regal Pillow | `REGAL_PILLOW` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Shovel | `SHOVEL` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Singing Bowl | `SINGING_BOWL` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Smiling Mask | `SMILING_MASK` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Spirit Poop | `SPIRIT_POOP` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Ssserpent Head | `SSSERPENT_HEAD` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Strawberry | `STRAWBERRY` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Tiny Chest | `TINY_CHEST` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Tiny House | `TINY_HOUSE` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Toxic Egg | `TOXIC_EGG` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Lees Waffle | `LEES_WAFFLE` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| War Paint | `WAR_PAINT` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Whetstone | `WHETSTONE` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| White Beast Statue | `WHITE_BEAST_STATUE` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |
| Wing Boots | `WING_BOOTS` | ownership_and_applicable_room_entry_hook | Existing public powers/counts or no battle progress |

## Reproduction

```powershell
python scripts/regenerate-relic-state-patch.py
& scripts/build-relic-state.ps1
$env:PYTHONPATH='C:/Users/19091/Desktop/sts2-relic-state-v1/third_party/sts_lightspeed/build'
python -m pytest tests/test_relic_remaining.py -q
python scripts/audit-relic-catalog.py
python scripts/check-spec-v6.py
```
