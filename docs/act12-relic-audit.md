# Full Act 1/2 relic scope and state audit

Date: 2026-09-19. Decision I10. Implementation baseline: `9d95526`.

## Scope and result

The complete local original-game relic class inventory was reconciled with RelicLibrary registration and the locked backend. There are **191 top-level relic class files**, including AbstractRelic; the matrix contains **190 concrete/reference entries**. **178** are registered by RelicLibrary. All **180 non-sentinel upstream enum entries** are accounted for, including two fallback/special entries outside ordinary registration. Class presence, original registration, Act 1/2 eligibility and runtime support are separate facts.

For a standard finite **Ironclad** run, treating unlockable entries as potential candidates:

| Scope | Entries |
|---|---:|
| Potential Act 1/2 acquisition or carry-in | 148 |
| Other-character pool | 29 |
| Act 3-only standard source: Mark of the Bloom | 1 |
| Fallback/special-mode Circlet and Red Circlet | 2 |
| Unregistered/deprecated concrete classes | 10 |

The 148 potential entries comprise 14 existing diagnostic imports, 8 second-batch candidates, 24 special-review items, 46 run/acquisition/cosmetic-effect entries and 56 later combat candidates. These categories are an implementation routing decision, not a support or runtime-equivalence claim. Several later candidates still need targeted state-semantic validation; their exact reference fields and hooks are retained rather than guessed away.

The audit includes carried relics, not just items awarded inside a particular act. Boss relics from the Act 1 chest can affect Act 2; the Act 2 chest occurs after its last battle. Neow boss swaps remain subject to their own eligibility and replacement rules. Ectoplasm's new-acquisition gate is Act 1, while ownership can persist into Act 2. Other-character relics are not made Ironclad-obtainable merely by owning Prismatic Shard. Daily/custom/endless modes require separate scope.

Detailed deliverables:

- [Full per-entry matrix](act12-relic-audit-matrix.md): identity, pool, scope, disposition and state risks.
- [Machine-readable audit](evidence/act12-relic-scope-audit.json): original IDs, class locations, hook names, instance-field metadata, acquisition conditions, backend source references, confidence and verification date.
- [Special-relic review](relic-special-review.md): proposed boundaries requiring owner approval before implementation.

## Sources and evidence boundary

Primary original source: the user's local `E:/SteamLibrary/steamapps/common/SlayTheSpire/desktop-1.0.jar`, SHA-256 `cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673`, rehashed on this date. Catalog registration and callback/state metadata were inspected for all entries. Targeted arbitration used RelicLibrary, AbstractDungeon pool/shrine gates, Exordium/TheCity event lists, individual second-batch relic methods, AbstractRoom.endBattle and AbstractPlayer.onVictory.

Backend source: locked `sts_lightspeed` commit `7476a81954020087da31d41d16fddf475746ec2d` plus the project's recorded patches. The backend ledger records actual source locations; an occurrence alone is not evidence that a mechanism is faithful or reachable through the adapter.

Original classes and CFR reference output remain under ignored `reference/relic-act12-audit/`. No original implementation is copied into simulator source or published in these documents. The committed audit contains identifiers, locations and independently written findings. CFR 0.152 was obtained from its author's distribution solely for local inspection.

**Completed:** complete static catalog/scope/state-risk review and second-batch mechanism arbitration. **Not claimed:** live original-game differential tests for all relics, exhaustive combinations, fully verified public-state encodings for every later candidate, or all-relic simulation support. Pending semantics are recorded per entry; they are not silently replaced by zero.

## Second batch and findings before import

| Relic | Required behavior and observation | Finding / acceptance target |
|---|---|---|
| Bag of Marbles | Opening enemy Vulnerable; actual enemy statuses | Existing backend hook; verify duration, Artifact and no duplicate entry trigger |
| Red Mask | Opening enemy Weak; actual enemy statuses | Existing backend hook; Act 2 event provenance, verify damage and Artifact |
| Clockwork Souvenir | Opening player Artifact | Existing backend hook; verify consumption by a real debuff and no reapplication |
| Preserved Insect | Elite-trigger initial HP reduction, preserve max HP | Existing backend hook; distinguish elite/boss/ordinary/event encounters; clamp rather than raise already-lower HP |
| Slaver's Collar | Additional energy in elite/boss combat | Existing backend hook; verify both acts, normal-room counterexample and subsequent reset |
| Black Blood | Single victory heal, replacing Burning Blood | Existing engine exit hook; reject simultaneous ownership and account from actual post-exit HP |
| Meat on the Bone | HP threshold checked before other victory relic healing | Existing exit-loop ordering is insufficient; correct the new-entry exit path with reference-derived tests |
| Orichalcum | End-turn block when starting end-turn with zero block | Existing backend hook; test positive-block counterexample and end-turn block-power interaction |

All eight can use identity plus already-public HP, block, energy, player/enemy statuses and scene encounter classification; no new generic counter is proposed. Orichalcum's reference `trigger` field defaults false and no nondefault writer was found in the inspected original classes outside the relic; its normal decision-boundary behavior is determined by public block. This does not authorize arbitrary mid-queue restoration.

### Exit-state defect

The old adapter heals Burning Blood directly before calling `exitBattle`, and `updateRelicsOnExit` heals it again in GameContext. The old returned observation uses BattleContext HP and therefore conceals the duplicated internal writeback. The new path must use **one** exit settlement and synchronize final public HP from its actual result.

Original AbstractRoom.endBattle calls Meat on the Bone before AbstractPlayer.onVictory invokes victory relic callbacks. The backend's ownership-ordered exit loop can test the HP threshold after another relic has healed, producing a different result. In the new relic entry only, evaluate the threshold once at the appropriate pre-victory-heal point, then settle existing victory effects once. Keep reward v2's formula unchanged; its HP input must be the corrected post-exit HP. Legacy entry behavior is retained for historical compatibility, with this defect disclosed rather than hidden.

### Other findings held out of this batch

- Clockwork Souvenir with Mutagenic Strength requires acquisition-order arbitration; the latter remains blocked for owner review and is not in the admitted new registry.
- Preserved Insect combined with Neow's Lament must never increase an enemy already below the target HP. Neow's Lament remains unimported; new-entry behavior should still avoid raising HP.
- Identity-only observations are insufficient for Ancient Tea Set, Girya, Lizard Tail, Neow's Lament, Pocketwatch, Orange Pellets and other listed stateful cases. The matrix names the required entry/history/state information.
- Bottled references, visibility-changing relics, generated-card closure, potion capacity and resurrection remain separate review items.

This report and its baseline matrix are produced **before** second-batch code changes. Subsequent integration/test results belong in the second-batch report; the baseline audit is not rewritten to imply those tests ran earlier.
