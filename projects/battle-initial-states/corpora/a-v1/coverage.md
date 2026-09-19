# A corpus coverage analysis

Date: 2026-09-19. Frozen diagnostic corpus; no formal training admission.

## Findings and implications

- Broad identity coverage is present: 39 encounter identities, including six ordinary elites and six bosses; 74 observed card identities, 118 relic identities and all 15 supported potion identities. Identity presence is not sufficient coverage of interactions.
- Act 1 has 1,004 states and Act 2 has 373. Act 2 retains only 373/1,161 raw combat occurrences (32.13%), versus 1,041/1,430 (72.80%) in Act 1. This is reconstruction/admission selection, not evidence that Act 2 is naturally rare.
- Act 2 accounts for 27.09% of states but 17.45% under equal-source-group weighting. Existing source weighting would emphasize early fights more than the unweighted table suggests.
- Only 24 states have HP at or below 25%, including four Act 2 states. Of the 156 observed-encounter by HP-band cells, 37 are empty. These are empirical coverage gaps, not claims that every combination should occur naturally.
- Potion projection affects 792 states. Empty inventories increase from 283 to 787; 504 previously nonempty inventories become empty. The projected corpus cannot establish historical potion-availability behavior.
- Combination probes have narrow independent support: Barricade plus Body Slam/Entrench has five states from one source group; Rupture plus a listed self-damage card has four from one group. Repeated states within those runs cannot support held-out-source generalization for those combinations.
- Persistent counter coverage is concentrated: Happy Flower, Incense Burner, Ink Bottle, Nunchaku, Pen Nib and Sundial appear only at zero in these entry states. Their identity counts do not cover alternative entry-counter phases.
- The 134-state audit holdout has only seven connected components. No group/component crosses partitions, but the holdout offers limited independent-source coverage.
- Searing Blow and Thunderclap are absent. Burn, Dazed, Slimed and Wound are also absent from entry master decks; their absence is not evidence that combat-generated status handling is absent.
- All 395 elite entries have a configured burning-elite field, and all 1,377 states have burning_elite=false. Burning-elite conditions are therefore absent.
- Holdout has 31 Act 2 states from five connected components. Five observed encounters are absent from holdout: CENTURION_AND_HEALER, CHAMP, CHOSEN_AND_BYRDS, LOTS_OF_SLIMES and TWO_THIEVES. Block-retention and self-damage probes occur only in audit-train; the Dropkick probe is also absent from holdout.

## Recommended bounded next steps

1. Use these frozen states for a source-component-separated baseline only with explicit Act, HP, encounter and projection strata. The analysis does not establish training sufficiency or learning performance.
2. Inspect existing holdout support for rare combinations before assigning evaluation claims. Do not split the same source component to manufacture train/test examples.
3. Prioritize low-HP Act 2, rare combination independence, persistent counter phases and scarce Act 2 bosses in any future coverage decision. No state generation or backend expansion is performed here.
4. Resolve the v1 wrapper versus v2 canonical-schema label before a later consumer integration; preserve this frozen corpus during analysis.

## Definitions and evidence

State counts use distinct canonical state hashes. Source coverage uses every provenance origin, not only the primary origin. Equal-group percentages first select an observed source group uniformly, then a state within it; this is a descriptive sensitivity analysis, not a changed sampler. Connected components remain the split boundary.

All input hashes, canonical state hashes and the runtime-state join were checked. Historical rules equivalence remains unverified. The corpus wrapper labels records v1 while canonical pilot records and hashing use v2; this naming inconsistency is recorded, not repaired by this analysis.

## Grain

```json
{
  "canonical_states": 1377,
  "origin_occurrences": 1414,
  "all_origin_source_groups": 141,
  "primary_source_groups": 138,
  "connected_components": 104,
  "cross_source_canonical_states": 16,
  "distinct_deck_multisets_with_upgrades": 1125,
  "distinct_deck_encounter_pairs": 1307,
  "largest_component_states": 73,
  "top10_component_states": 372
}
```

## Coverage tables

### act

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| 1 | 1004 | 72.91 | 141 | 104 | 82.55 |
| 2 | 373 | 27.09 | 81 | 69 | 17.45 |

### floor

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| 1 | 102 | 7.41 | 139 | 102 | 17.55 |
| 10 | 61 | 4.43 | 61 | 50 | 4.03 |
| 11 | 56 | 4.07 | 56 | 47 | 3.49 |
| 12 | 56 | 4.07 | 56 | 50 | 3.27 |
| 13 | 54 | 3.92 | 54 | 50 | 3.17 |
| 14 | 80 | 5.81 | 80 | 67 | 4.61 |
| 16 | 88 | 6.39 | 88 | 74 | 4.97 |
| 18 | 81 | 5.88 | 81 | 69 | 4.45 |
| 19 | 27 | 1.96 | 27 | 25 | 1.34 |
| 2 | 84 | 6.1 | 84 | 68 | 7.93 |
| 20 | 32 | 2.32 | 32 | 27 | 1.6 |
| 21 | 17 | 1.23 | 17 | 16 | 0.79 |
| 22 | 27 | 1.96 | 27 | 26 | 1.23 |
| 23 | 29 | 2.11 | 29 | 25 | 1.35 |
| 24 | 19 | 1.38 | 19 | 18 | 0.84 |
| 25 | 25 | 1.82 | 25 | 23 | 1.13 |
| 27 | 23 | 1.67 | 23 | 22 | 0.95 |
| 28 | 20 | 1.45 | 20 | 19 | 0.83 |
| 29 | 22 | 1.6 | 22 | 20 | 0.9 |
| 3 | 78 | 5.66 | 78 | 62 | 6.79 |
| 30 | 13 | 0.94 | 13 | 12 | 0.5 |
| 31 | 18 | 1.31 | 18 | 18 | 0.73 |
| 33 | 20 | 1.45 | 20 | 19 | 0.81 |
| 4 | 76 | 5.52 | 76 | 65 | 6.6 |
| 5 | 69 | 5.01 | 69 | 61 | 5.23 |
| 6 | 61 | 4.43 | 61 | 51 | 4.55 |
| 7 | 70 | 5.08 | 70 | 58 | 5.43 |
| 8 | 69 | 5.01 | 69 | 57 | 4.94 |

### ascension

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| 20 | 1377 | 100.0 | 141 | 104 | 100.0 |

### encounter

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| AUTOMATON | 4 | 0.29 | 4 | 4 | 0.17 |
| BLUE_SLAVER | 37 | 2.69 | 37 | 32 | 2.66 |
| BOOK_OF_STABBING | 35 | 2.54 | 32 | 29 | 1.53 |
| CENTURION_AND_HEALER | 24 | 1.74 | 22 | 21 | 1.01 |
| CHAMP | 9 | 0.65 | 9 | 9 | 0.35 |
| CHOSEN | 27 | 1.96 | 27 | 26 | 1.36 |
| CHOSEN_AND_BYRDS | 7 | 0.51 | 6 | 6 | 0.28 |
| COLLECTOR | 7 | 0.51 | 7 | 7 | 0.29 |
| CULTIST | 98 | 7.12 | 106 | 81 | 10.29 |
| CULTIST_AND_CHOSEN | 12 | 0.87 | 11 | 11 | 0.51 |
| EXORDIUM_THUGS | 30 | 2.18 | 30 | 28 | 1.7 |
| EXORDIUM_WILDLIFE | 21 | 1.53 | 21 | 20 | 1.24 |
| GREMLIN_GANG | 17 | 1.23 | 17 | 13 | 1.21 |
| GREMLIN_LEADER | 35 | 2.54 | 31 | 28 | 1.56 |
| GREMLIN_NOB | 93 | 6.75 | 83 | 67 | 6.23 |
| HEXAGHOST | 24 | 1.74 | 24 | 21 | 1.36 |
| JAW_WORM | 91 | 6.61 | 93 | 79 | 9.07 |
| LAGAVULIN | 97 | 7.04 | 87 | 75 | 6.99 |
| LARGE_SLIME | 33 | 2.4 | 32 | 30 | 2.06 |
| LOOTER | 33 | 2.4 | 32 | 29 | 2.37 |
| LOTS_OF_SLIMES | 11 | 0.8 | 11 | 10 | 0.62 |
| RED_SLAVER | 20 | 1.45 | 20 | 17 | 1.3 |
| SENTRY_AND_SPHERE | 7 | 0.51 | 7 | 7 | 0.28 |
| SHELLED_PARASITE_AND_FUNGI | 17 | 1.23 | 17 | 16 | 0.73 |
| SHELL_PARASITE | 23 | 1.67 | 23 | 22 | 1.25 |
| SLAVERS | 31 | 2.25 | 28 | 24 | 1.33 |
| SLIME_BOSS | 36 | 2.61 | 36 | 36 | 1.99 |
| SMALL_SLIMES | 84 | 6.1 | 96 | 75 | 9.32 |
| SNAKE_PLANT | 20 | 1.45 | 20 | 19 | 0.85 |
| SNECKO | 11 | 0.8 | 11 | 11 | 0.5 |
| SPHERIC_GUARDIAN | 36 | 2.61 | 36 | 34 | 1.93 |
| THE_GUARDIAN | 28 | 2.03 | 28 | 25 | 1.62 |
| THREE_BYRDS | 31 | 2.25 | 31 | 26 | 1.71 |
| THREE_CULTIST | 13 | 0.94 | 13 | 12 | 0.61 |
| THREE_LOUSE | 28 | 2.03 | 28 | 28 | 1.82 |
| THREE_SENTRIES | 104 | 7.55 | 88 | 74 | 7.36 |
| TWO_FUNGI_BEASTS | 34 | 2.47 | 34 | 32 | 1.91 |
| TWO_LOUSE | 85 | 6.17 | 100 | 80 | 11.43 |
| TWO_THIEVES | 24 | 1.74 | 24 | 22 | 1.19 |

### encounter_kind

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| boss | 108 | 7.84 | 88 | 74 | 5.79 |
| elite | 395 | 28.69 | 121 | 94 | 24.99 |
| normal | 874 | 63.47 | 141 | 104 | 69.22 |

### hp_band

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| 25-50% | 185 | 13.44 | 71 | 61 | 10.52 |
| 50-75% | 397 | 28.83 | 107 | 83 | 26.44 |
| <=25% | 24 | 1.74 | 21 | 21 | 1.37 |
| >75% | 771 | 55.99 | 137 | 103 | 61.67 |

### act_hp

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| 1 / 25-50% | 149 | 10.82 | 65 | 56 | 8.88 |
| 1 / 50-75% | 301 | 21.86 | 100 | 77 | 22.06 |
| 1 / <=25% | 20 | 1.45 | 17 | 17 | 1.2 |
| 1 / >75% | 534 | 38.78 | 136 | 102 | 50.4 |
| 2 / 25-50% | 36 | 2.61 | 19 | 17 | 1.64 |
| 2 / 50-75% | 96 | 6.97 | 41 | 35 | 4.38 |
| 2 / <=25% | 4 | 0.29 | 4 | 4 | 0.17 |
| 2 / >75% | 237 | 17.21 | 81 | 69 | 11.26 |

### act_kind

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| 1 / boss | 88 | 6.39 | 88 | 74 | 4.97 |
| 1 / elite | 294 | 21.35 | 121 | 94 | 20.58 |
| 1 / normal | 622 | 45.17 | 141 | 104 | 57.0 |
| 2 / boss | 20 | 1.45 | 20 | 19 | 0.81 |
| 2 / elite | 101 | 7.33 | 44 | 38 | 4.41 |
| 2 / normal | 252 | 18.3 | 81 | 69 | 12.22 |

### potion_occupancy

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| 0 | 787 | 57.15 | 140 | 103 | 62.43 |
| 1 | 493 | 35.8 | 112 | 85 | 31.16 |
| 2 | 97 | 7.04 | 44 | 34 | 6.42 |

### source_potion_occupancy

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| 0 | 283 | 20.55 | 139 | 102 | 32.48 |
| 1 | 450 | 32.68 | 127 | 98 | 30.78 |
| 2 | 644 | 46.77 | 112 | 87 | 36.74 |

### potion_transition

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| 0->0 | 283 | 20.55 | 139 | 102 | 32.48 |
| 1->0 | 245 | 17.79 | 95 | 77 | 16.21 |
| 1->1 | 205 | 14.89 | 84 | 66 | 14.58 |
| 2->0 | 259 | 18.81 | 63 | 56 | 13.74 |
| 2->1 | 288 | 20.92 | 92 | 76 | 16.58 |
| 2->2 | 97 | 7.04 | 44 | 34 | 6.42 |

### partition

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| audit-dev | 199 | 14.45 | 25 | 13 | 17.73 |
| audit-holdout | 134 | 9.73 | 15 | 7 | 10.64 |
| audit-train | 1044 | 75.82 | 101 | 84 | 71.63 |

### partition_act

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| audit-dev / 1 | 153 | 11.11 | 25 | 13 | 15.32 |
| audit-dev / 2 | 46 | 3.34 | 12 | 8 | 2.41 |
| audit-holdout / 1 | 103 | 7.48 | 15 | 7 | 9.25 |
| audit-holdout / 2 | 31 | 2.25 | 7 | 5 | 1.39 |
| audit-train / 1 | 748 | 54.32 | 101 | 84 | 57.98 |
| audit-train / 2 | 296 | 21.5 | 62 | 56 | 13.65 |

### burning_elite

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| False | 1377 | 100.0 | 141 | 104 | 100.0 |

### Combination presence probes (overlapping; not archetype certification)

| Value | States | State % | Source groups | Components | Equal-group % |
|---|---:|---:|---:|---:|---:|
| exhaust-engine | 74 | 5.37 | 15 | 14 | 3.56 |
| strength-payoff | 121 | 8.79 | 17 | 16 | 5.65 |
| block-retention-payoff | 5 | 0.36 | 1 | 1 | 0.24 |
| status-payoff | 122 | 8.86 | 17 | 16 | 5.77 |
| self-damage-payoff | 4 | 0.29 | 1 | 1 | 0.18 |
| dropkick-weak | 14 | 1.02 | 3 | 3 | 0.61 |

## Cards

| Identity | States | Source groups | Encounter identities | Upgraded states |
|---|---:|---:|---:|---:|
| Burn | 0 | 0 | 0 | 0 |
| Dazed | 0 | 0 | 0 | 0 |
| Searing Blow | 0 | 0 | 0 | 0 |
| Slimed | 0 | 0 | 0 | 0 |
| Thunderclap | 0 | 0 | 0 | 0 |
| Wound | 0 | 0 | 0 | 0 |
| Rupture | 4 | 1 | 4 | 4 |
| Sentinel | 6 | 2 | 6 | 0 |
| Entrench | 9 | 2 | 7 | 4 |
| Sword Boomerang | 10 | 2 | 10 | 5 |
| Dual Wield | 13 | 5 | 10 | 6 |
| Dropkick | 14 | 3 | 11 | 0 |
| Limit Break | 19 | 2 | 18 | 0 |
| Clash | 20 | 3 | 16 | 0 |
| Juggernaut | 20 | 3 | 15 | 0 |
| Heavy Blade | 22 | 3 | 22 | 10 |
| Fire Breathing | 26 | 4 | 20 | 0 |
| Barricade | 27 | 7 | 23 | 0 |
| Berserk | 28 | 5 | 21 | 18 |
| Rage | 28 | 6 | 20 | 14 |
| True Grit | 30 | 6 | 14 | 21 |
| Flex | 32 | 5 | 22 | 21 |
| Exhume | 38 | 13 | 24 | 5 |
| Intimidate | 38 | 6 | 21 | 10 |
| Warcry | 38 | 6 | 23 | 19 |
| Brutality | 39 | 7 | 22 | 2 |
| Reckless Charge | 41 | 5 | 26 | 0 |
| Havoc | 45 | 9 | 26 | 21 |
| Sever Soul | 49 | 5 | 24 | 25 |
| Wild Strike | 50 | 6 | 30 | 9 |
| Rampage | 52 | 6 | 24 | 0 |
| Body Slam | 56 | 12 | 28 | 19 |
| Ghostly Armor | 61 | 9 | 29 | 12 |
| Pummel | 70 | 8 | 32 | 11 |
| Combust | 72 | 8 | 29 | 16 |
| Bludgeon | 73 | 8 | 30 | 56 |
| Infernal Blade | 74 | 9 | 31 | 25 |
| Demon Form | 77 | 11 | 33 | 2 |
| Double Tap | 94 | 11 | 33 | 21 |
| Dark Embrace | 98 | 17 | 31 | 37 |
| Seeing Red | 103 | 15 | 35 | 12 |
| Reaper | 105 | 17 | 29 | 0 |
| Impervious | 121 | 19 | 35 | 8 |
| Clothesline | 122 | 15 | 35 | 20 |
| Metallicize | 123 | 17 | 36 | 7 |
| Burning Pact | 124 | 21 | 38 | 30 |
| Flame Barrier | 126 | 22 | 36 | 24 |
| Disarm | 128 | 24 | 34 | 6 |
| Evolve | 134 | 17 | 35 | 3 |
| Feed | 141 | 26 | 37 | 23 |
| Cleave | 142 | 13 | 33 | 36 |
| Corruption | 145 | 27 | 36 | 59 |
| Offering | 145 | 25 | 35 | 38 |
| Uppercut | 155 | 23 | 35 | 80 |
| Fiend Fire | 159 | 24 | 37 | 90 |
| Second Wind | 160 | 24 | 38 | 18 |
| Carnage | 166 | 21 | 37 | 108 |
| Hemokinesis | 167 | 21 | 37 | 55 |
| Feel No Pain | 168 | 28 | 37 | 22 |
| Immolate | 168 | 22 | 38 | 119 |
| Spot Weakness | 174 | 23 | 39 | 45 |
| Blood for Blood | 177 | 24 | 39 | 111 |
| Perfected Strike | 177 | 22 | 38 | 64 |
| Battle Trance | 181 | 27 | 38 | 46 |
| Whirlwind | 184 | 22 | 38 | 148 |
| Bloodletting | 185 | 24 | 37 | 18 |
| Iron Wave | 200 | 26 | 36 | 22 |
| Power Through | 206 | 31 | 37 | 32 |
| Inflame | 218 | 25 | 38 | 133 |
| Twin Strike | 243 | 32 | 38 | 25 |
| Shockwave | 269 | 30 | 39 | 65 |
| Armaments | 283 | 33 | 38 | 203 |
| Headbutt | 337 | 41 | 39 | 0 |
| Shrug It Off | 355 | 61 | 39 | 60 |
| Pommel Strike | 447 | 63 | 39 | 189 |
| Anger | 481 | 58 | 39 | 39 |
| Strike_R | 1371 | 141 | 39 | 115 |
| AscendersBane | 1377 | 141 | 39 | 0 |
| Bash | 1377 | 141 | 39 | 170 |
| Defend_R | 1377 | 141 | 39 | 88 |

## Relics

| Identity | States | Source groups | Encounter identities | Upgraded states |
|---|---:|---:|---:|---:|
| Bloody Idol | 0 | 0 | 0 | N/A |
| Cauldron | 0 | 0 | 0 | N/A |
| Cultist Headpiece | 0 | 0 | 0 | N/A |
| Dollys Mirror | 0 | 0 | 0 | N/A |
| Ectoplasm | 0 | 0 | 0 | N/A |
| Gremlin Visage | 0 | 0 | 0 | N/A |
| Hand Drill | 0 | 0 | 0 | N/A |
| Nloths Hungry Face | 0 | 0 | 0 | N/A |
| Odd Mushroom | 0 | 0 | 0 | N/A |
| Orange Pellets | 0 | 0 | 0 | N/A |
| Red Mask | 0 | 0 | 0 | N/A |
| Runic Dome | 0 | 0 | 0 | N/A |
| Spirit Poop | 0 | 0 | 0 | N/A |
| Ssserpent Head | 0 | 0 | 0 | N/A |
| Thread and Needle | 0 | 0 | 0 | N/A |
| Tiny House | 0 | 0 | 0 | N/A |
| Wing Boots | 0 | 0 | 0 | N/A |
| Black Blood | 1 | 1 | 1 | N/A |
| Mutagenic Strength | 1 | 1 | 1 | N/A |
| Pocketwatch | 1 | 1 | 1 | N/A |
| Nloths Gift | 2 | 1 | 2 | N/A |
| Du-Vu Doll | 3 | 2 | 3 | N/A |
| Pear | 4 | 2 | 3 | N/A |
| Sozu | 4 | 3 | 3 | N/A |
| Black Star | 5 | 1 | 5 | N/A |
| Bottled Flame | 5 | 1 | 5 | N/A |
| Prayer Wheel | 5 | 1 | 5 | N/A |
| Lees Waffle | 6 | 1 | 6 | N/A |
| Ginger | 7 | 1 | 7 | N/A |
| Sling of Courage | 7 | 1 | 5 | N/A |
| Bottled Tornado | 8 | 3 | 5 | N/A |
| Empty Cage | 8 | 1 | 8 | N/A |
| Face of Cleric | 9 | 1 | 9 | N/A |
| Slaver's Collar | 9 | 3 | 6 | N/A |
| Velvet Choker | 9 | 3 | 7 | N/A |
| Warped Tongs | 9 | 2 | 8 | N/A |
| Calling Bell | 11 | 2 | 9 | N/A |
| Charon's Ashes | 13 | 2 | 11 | N/A |
| Girya | 13 | 2 | 9 | N/A |
| Tungsten Rod | 13 | 2 | 12 | N/A |
| Chemical X | 14 | 1 | 13 | N/A |
| Pandoras Box | 15 | 8 | 9 | N/A |
| Busted Crown | 16 | 1 | 15 | N/A |
| Mango | 16 | 3 | 15 | N/A |
| Mark of Pain | 17 | 3 | 10 | N/A |
| Membership Card | 17 | 5 | 14 | N/A |
| Peace Pipe | 18 | 2 | 17 | N/A |
| Bottled Lightning | 19 | 4 | 16 | N/A |
| Calipers | 20 | 3 | 14 | N/A |
| Captain's Wheel | 20 | 4 | 14 | N/A |
| Shovel | 20 | 2 | 15 | N/A |
| Turnip | 20 | 4 | 16 | N/A |
| Letter Opener | 22 | 6 | 18 | N/A |
| Philosopher's Stone | 22 | 5 | 16 | N/A |
| The Abacus | 22 | 3 | 12 | N/A |
| Eternal Feather | 23 | 6 | 18 | N/A |
| Ice Cream | 23 | 3 | 20 | N/A |
| Juzu Bracelet | 23 | 4 | 17 | N/A |
| Champion's Belt | 24 | 3 | 17 | N/A |
| Magic Flower | 24 | 3 | 18 | N/A |
| Brimstone | 25 | 3 | 19 | N/A |
| Mummified Hand | 25 | 4 | 18 | N/A |
| Bronze Scales | 26 | 6 | 20 | N/A |
| Fossilized Helix | 26 | 4 | 22 | N/A |
| Torii | 26 | 3 | 19 | N/A |
| Clockwork Souvenir | 27 | 5 | 19 | N/A |
| Fusion Hammer | 28 | 5 | 15 | N/A |
| Whetstone | 29 | 4 | 21 | N/A |
| Runic Cube | 30 | 6 | 15 | N/A |
| The Boot | 30 | 6 | 20 | N/A |
| Cursed Key | 31 | 8 | 16 | N/A |
| Regal Pillow | 31 | 6 | 25 | N/A |
| Frozen Eye | 33 | 7 | 25 | N/A |
| Meat on the Bone | 33 | 5 | 24 | N/A |
| Smiling Mask | 33 | 6 | 22 | N/A |
| Matryoshka | 34 | 6 | 21 | N/A |
| Molten Egg | 34 | 5 | 26 | N/A |
| Orrery | 34 | 7 | 19 | N/A |
| Singing Bowl | 34 | 6 | 19 | N/A |
| Stone Calendar | 34 | 5 | 23 | N/A |
| Astrolabe | 35 | 5 | 25 | N/A |
| Neow's Lament | 35 | 6 | 17 | N/A |
| Darkstone Periapt | 37 | 5 | 25 | N/A |
| Incense Burner | 37 | 5 | 22 | N/A |
| Kunai | 37 | 9 | 23 | N/A |
| Blood Vial | 40 | 5 | 24 | N/A |
| Mercury Hourglass | 40 | 7 | 25 | N/A |
| Sundial | 40 | 7 | 25 | N/A |
| Strike Dummy | 41 | 4 | 20 | N/A |
| Tiny Chest | 41 | 7 | 27 | N/A |
| White Beast Statue | 41 | 5 | 25 | N/A |
| Dream Catcher | 42 | 8 | 27 | N/A |
| The Courier | 43 | 6 | 25 | N/A |
| Frozen Egg | 45 | 6 | 26 | N/A |
| Old Coin | 45 | 6 | 27 | N/A |
| Oddly Smooth Stone | 46 | 10 | 25 | N/A |
| Shuriken | 46 | 9 | 26 | N/A |
| Question Card | 47 | 9 | 26 | N/A |
| Ornamental Fan | 51 | 6 | 25 | N/A |
| Snecko Eye | 52 | 10 | 21 | N/A |
| Gremlin Horn | 53 | 7 | 23 | N/A |
| Maw Bank | 53 | 9 | 27 | N/A |
| Runic Pyramid | 54 | 10 | 18 | N/A |
| Happy Flower | 55 | 12 | 27 | N/A |
| Red Skull | 56 | 9 | 29 | N/A |
| Toxic Egg | 56 | 7 | 28 | N/A |
| Toy Ornithopter | 56 | 10 | 28 | N/A |
| Ceramic Fish | 57 | 10 | 27 | N/A |
| Ink Bottle | 57 | 8 | 27 | N/A |
| Meal Ticket | 57 | 8 | 26 | N/A |
| Orichalcum | 57 | 6 | 27 | N/A |
| Unceasing Top | 57 | 5 | 30 | N/A |
| Art of War | 60 | 9 | 29 | N/A |
| Bird-Faced Urn | 62 | 6 | 31 | N/A |
| Horn Cleat | 63 | 8 | 29 | N/A |
| Coffee Dripper | 64 | 11 | 18 | N/A |
| Paper Phrog | 65 | 10 | 26 | N/A |
| Vajra | 68 | 12 | 31 | N/A |
| Nunchaku | 69 | 13 | 27 | N/A |
| War Paint | 69 | 10 | 31 | N/A |
| Preserved Insect | 72 | 10 | 33 | N/A |
| Ancient Tea Set | 75 | 10 | 30 | N/A |
| Bag of Marbles | 75 | 11 | 29 | N/A |
| Pen Nib | 76 | 12 | 32 | N/A |
| Anchor | 77 | 14 | 32 | N/A |
| Pantograph | 77 | 11 | 31 | N/A |
| Strawberry | 79 | 12 | 30 | N/A |
| Omamori | 86 | 15 | 32 | N/A |
| Self-Forming Clay | 87 | 11 | 31 | N/A |
| Lantern | 90 | 15 | 32 | N/A |
| Akabeko | 92 | 9 | 34 | N/A |
| Centennial Puzzle | 102 | 13 | 36 | N/A |
| Golden Idol | 121 | 21 | 26 | N/A |
| Bag of Preparation | 126 | 17 | 37 | N/A |
| Burning Blood | 1376 | 141 | 39 | N/A |

## Supported potions

| Identity | States | Source groups | Encounter identities | Upgraded states |
|---|---:|---:|---:|---:|
| Fruit Juice | 10 | 7 | 9 | N/A |
| Ancient Potion | 15 | 5 | 13 | N/A |
| HeartOfIron | 26 | 9 | 21 | N/A |
| LiquidBronze | 31 | 13 | 15 | N/A |
| Block Potion | 34 | 14 | 22 | N/A |
| Dexterity Potion | 38 | 16 | 18 | N/A |
| EssenceOfSteel | 38 | 18 | 22 | N/A |
| Regen Potion | 40 | 16 | 27 | N/A |
| SpeedPotion | 41 | 18 | 22 | N/A |
| Swift Potion | 48 | 16 | 28 | N/A |
| Explosive Potion | 59 | 18 | 28 | N/A |
| Strength Potion | 67 | 18 | 31 | N/A |
| Energy Potion | 74 | 21 | 28 | N/A |
| Weak Potion | 74 | 28 | 30 | N/A |
| FearPotion | 82 | 23 | 32 | N/A |

## Interpretation limits

- Card/relic presence and combination probes do not demonstrate learned use or successful synergy execution.
- Floors without combat entries are not automatically coverage defects; no denominator of all possible game states is claimed.
- Registry absence is a development-scope comparison; the expansion encounter registry includes out-of-scope encounters.
- Configured fields and potion projection alter the training instance distribution; counts remain separate in the JSON.
- Full episode evidence covers a representative subset only; reset validation is broader.

## Reproduction

`python -B projects/battle-initial-states/analyze-a-coverage.py`

Detailed cross-tabs, retention denominators, probe rules, numeric summaries and immutable input fingerprints: [a-corpus-coverage.json](a-corpus-coverage.json).
