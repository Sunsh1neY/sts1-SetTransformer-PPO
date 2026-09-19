# Remaining relic import scope

Date: 2026-09-19. Implementation baseline: `58448c7`.

## Original queue at the implementation baseline

148 Act 1/2 candidates = 33 imported + 56 pending combat entries + 46 pending run/acquisition entries + 12 owner exclusions + 1 deferred Gambling Chip. Therefore 102 additional entries remain eligible for the approved import under the existing exclusions. The historical static audit is preserved unchanged.

## Approved scope (I13)

Owner approved: continue the combat-only project boundary. Import and verify the 56 combat entries. For the other 46, represent ownership and consume explicitly supplied post-acquisition deck/HP/gold/state; do not replay prior acquisition effects or claim shop, chest, campfire, map or reward-screen execution. Required backend continuation state must not be guessed. If an allegedly run-only item has an actual combat/exit hook, validate that hook before accepting it.

Not selected: full run-transition execution. Existing exclusions remain unchanged. Current implementation and validation are tracked in [the execution report](relic-remaining-report.md).

The 46-entry classification is inherited from the full audit and is a review queue, not proof of zero combat effect. No registry/runtime changes are made by this document.

## 56 combat entries in the original queue

| Original class | Backend identity | State assessment |
|---|---|---|

| Abacus | THE_ABACUS | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Akabeko | AKABEKO | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| AncientTeaSet | ANCIENT_TEA_SET | Rest-room carry-in eligibility and first-turn consumption; require explicit entry context. |

| ArtOfWar | ART_OF_WAR | Whether an attack was played last/current turn and first-turn state. |

| BirdFacedUrn | BIRD_FACED_URN | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| BloodyIdol | BLOODY_IDOL | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Boot | THE_BOOT | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Brimstone | BRIMSTONE | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| BustedCrown | BUSTED_CROWN | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Calipers | CALIPERS | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| CaptainsWheel | CAPTAINS_WHEEL | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| CentennialPuzzle | CENTENNIAL_PUZZLE | First HP-loss trigger used_this_combat; queued draw timing. |

| ChampionsBelt | CHAMPION_BELT | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| CharonsAshes | CHARONS_ASHES | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| ChemicalX | CHEMICAL_X | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| CoffeeDripper | COFFEE_DRIPPER | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| CursedKey | CURSED_KEY | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| DuVuDoll | DU_VU_DOLL | Master-deck curse count, distinct from transient combat cards. |

| Ectoplasm | ECTOPLASM | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| FaceOfCleric | FACE_OF_CLERIC | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| FossilizedHelix | FOSSILIZED_HELIX | Remaining buffer is public player status; entry application must occur once. |

| FusionHammer | FUSION_HAMMER | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Ginger | GINGER | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Girya | GIRYA | Persistent rest-site lift count (0..3); cannot infer it from ownership. |

| GremlinHorn | GREMLIN_HORN | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| GremlinMask | GREMLIN_VISAGE | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| HandDrill | HAND_DRILL | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| HornCleat | HORN_CLEAT | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| IceCream | ICE_CREAM | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Kunai | KUNAI | Attack progress within this turn; shared attack history only if event semantics match. |

| LetterOpener | LETTER_OPENER | Skill progress within this turn; reset at the proper turn boundary. |

| MagicFlower | MAGIC_FLOWER | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| MarkOfPain | MARK_OF_PAIN | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| MercuryHourglass | MERCURY_HOURGLASS | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| MummifiedHand | MUMMIFIED_HAND | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| NeowsLament | NEOWS_LAMENT | Remaining protected combats and entry consumption; persistent state required. |

| OddMushroom | ODD_MUSHROOM | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| OrnamentalFan | ORNAMENTAL_FAN | Attack progress within this turn; shared history must match event semantics. |

| Pantograph | PANTOGRAPH | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| PaperFrog | PAPER_PHROG | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| PhilosopherStone | PHILOSOPHERS_STONE | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Pocketwatch | POCKETWATCH | Previous-turn card count and first-turn state, not just current-turn statistics. |

| RedSkull | RED_SKULL | HP-threshold active state and applied Strength; avoid double application on restore. |

| RunicCube | RUNIC_CUBE | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| SelfFormingClay | SELF_FORMING_CLAY | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Shuriken | SHURIKEN | Attack progress within this turn; shared history must match event semantics. |

| Sling | SLING_OF_COURAGE | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Sozu | SOZU | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| StoneCalendar | STONE_CALENDAR | Combat turn/trigger progress; verify seventh-turn scheduling. |

| StrikeDummy | STRIKE_DUMMY | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| ThreadAndNeedle | THREAD_AND_NEEDLE | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Torii | TORII | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| ToyOrnithopter | TOY_ORNITHOPTER | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| TungstenRod | TUNGSTEN_ROD | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Turnip | TURNIP | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| WarpedTongs | WARPED_TONGS | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

## 46 run/acquisition entries in the original queue

| Original class | Backend identity | State assessment |
|---|---|---|

| Astrolabe | ASTROLABE | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| BlackStar | BLACK_STAR | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| CallingBell | CALLING_BELL | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| Cauldron | CAULDRON | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| CeramicFish | CERAMIC_FISH | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| Courier | THE_COURIER | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| CultistMask | CULTIST_HEADPIECE | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| DarkstonePeriapt | DARKSTONE_PERIAPT | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| DollysMirror | DOLLYS_MIRROR | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| DreamCatcher | DREAM_CATCHER | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| EmptyCage | EMPTY_CAGE | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| EternalFeather | ETERNAL_FEATHER | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| FrozenEgg2 | FROZEN_EGG | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| GoldenIdol | GOLDEN_IDOL | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| JuzuBracelet | JUZU_BRACELET | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| Mango | MANGO | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| Matryoshka | MATRYOSHKA | Persistent remaining chest uses; relevant to run state, not a new battle counter. |

| MawBank | MAW_BANK | Persistent spent state after spending gold; entry/run transition provenance. |

| MealTicket | MEAL_TICKET | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| MembershipCard | MEMBERSHIP_CARD | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| MoltenEgg2 | MOLTEN_EGG | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| NlothsGift | NLOTHS_GIFT | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| NlothsMask | NLOTHS_HUNGRY_FACE | Persistent next-chest suppression consumed/spent state. |

| OldCoin | OLD_COIN | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| Omamori | OMAMORI | Persistent remaining curse-prevention charges. |

| Orrery | ORRERY | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| PandorasBox | PANDORAS_BOX | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| PeacePipe | PEACE_PIPE | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| Pear | PEAR | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| PrayerWheel | PRAYER_WHEEL | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| QuestionCard | QUESTION_CARD | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| RegalPillow | REGAL_PILLOW | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| Shovel | SHOVEL | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| SingingBowl | SINGING_BOWL | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| SmilingMask | SMILING_MASK | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| SpiritPoop | SPIRIT_POOP | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| SsserpentHead | SSSERPENT_HEAD | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| Strawberry | STRAWBERRY | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| TinyChest | TINY_CHEST | Persistent unknown-room progress; run state only. |

| TinyHouse | TINY_HOUSE | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| ToxicEgg2 | TOXIC_EGG | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| Waffle | LEES_WAFFLE | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| WarPaint | WAR_PAINT | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| Whetstone | WHETSTONE | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| WhiteBeast | WHITE_BEAST_STATUE | Preserve ownership and actual configured deck/HP/gold/run effects; no new battle-only counter inferred. Run-history fields remain required for exact run continuation. |

| WingBoots | WING_BOOTS | Persistent remaining path bypass charges; run state only. |

## 13 excluded or deferred entries

| Original class | Backend identity | State assessment |
|---|---|---|

| BlueCandle | BLUE_CANDLE | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| DeadBranch | DEAD_BRANCH | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Enchiridion | ENCHIRIDION | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| GamblingChip | GAMBLING_CHIP | Opening trigger consumed plus explicit discard selection and continuation. |

| LizardTail | LIZARD_TAIL | Persistent spent/remaining-use state; lethal interception and resurrection order. |

| MedicalKit | MEDICAL_KIT | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Necronomicon | NECRONOMICON | Used_this_turn, replay eligibility and curse/deck effect; replay source context. |

| NilrysCodex | NILRYS_CODEX | Explicit end-turn offer, optional selection, generation and continuation. |

| PotionBelt | POTION_BELT | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| PrismaticShard | PRISMATIC_SHARD | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| SacredBark | SACRED_BARK | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| StrangeSpoon | STRANGE_SPOON | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |

| Toolbox | TOOLBOX | Identity plus existing public player/card/enemy state is the initial proposal; verify external rule hooks and restoration before import. |
