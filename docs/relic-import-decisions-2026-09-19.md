# Relic Import Decisions

Date: 2026-09-19

Status: Approved owner decisions.

## 1. Entity relation

Approved.

Relic-to-card binding uses the same general entity-relation concept as the existing Bronze Orb / Stasis card relation.

Bottled Flame, Bottled Lightning, and Bottled Tornado are approved to use an explicit relic-to-card relation rather than slot-based binding.

Entity references are used only to preserve the binding between concrete entities. Slot numbers are not part of model semantics.

## 2. Selection relics

### Nilry's Codex

Not imported. The owner's follow-up supersedes the earlier approval.

### Toolbox

Not imported.

Reason: Toolbox generates Colorless cards, which would expand the currently supported card scope.

### Gambling Chip

Conditional on an existing complete multi-selection, deselection and finish interface. Current public SelectionRouter supports exactly one choice and has no such complete flow; defer import. Backend internals alone do not satisfy this condition.

## 3. Information-visibility relics

### Frozen Eye

Approved for import.

The card observation may add the following public draw-order fields:

- `draw_position_known`
- `draw_position`

Frozen Eye exposes the observable draw-pile order through these fields.

Replace known_top in the new observation version with the same draw-position representation, including Headbutt and other verified known-top effects. Do not retain redundant parallel fields. Preserve historical frozen schemas. Define zero-based position 0 as the next card to draw, with an explicit known flag; unknown positions do not reveal hidden pile order.

### Runic Dome

Approved for import.

The simulator may retain the true enemy intent internally for game resolution, while the policy-facing public observation hides the current enemy intent when Runic Dome is owned.

Previously observed public history remains observable. Hide all direct encodings of current intent, including relevant damage/hit/type/move fields. History must contain actually observed public actions or information, not backend planned moves that were hidden at the time.

## 4. Stateful relic observation principle

Approved principle:

> Only export the minimal public state that affects future decisions and cannot be reconstructed unambiguously from the current policy-facing observation. Backend access and unprovided historical trajectories do not count as reconstruction from current observation.

If a relic state can already be derived from current public card, player, enemy, action, or other observable state, no duplicate relic counter is added.

This observation principle never permits omission or guessing of required simulator initial/recovery state.

A shared relic scalar counter may be used when a relic's required state is genuinely one-dimensional and the counter has clear semantics for that relic.

### Orange Pellets

Approved to use three explicit public state bits:

- attack played
- skill played
- power played

These states are not collapsed into a single generic scalar counter.

## 5. Relics formally frozen out of scope

The following relics are not imported in the current scope:

- Lizard Tail
- Necronomicon
- Nilry's Codex
- Dead Branch
- Enchiridion
- Prismatic Shard
- Blue Candle
- Medical Kit
- Sacred Bark
- Strange Spoon
- Toolbox

These relics remain excluded rather than being partially simulated or silently degraded.

## 6. Potion / capacity-related exclusions

The following relic is not imported in the current scope:

- Potion Belt

Sacred Bark is already excluded under the previous section.

These exclusions are formally frozen for the current relic-import scope.

## 7. Follow-up decisions and implementation findings

- **Unceasing Top:** import using backend automatic resolution and existing public fields; no additional relic field. Verify that any internal suppression flag cannot distinguish otherwise identical policy decision states. If it can, report the concrete counterexample before changing the approved field scope.
- **Runic Pyramid:** import using existing hand/card/energy state and backend retention; no additional relic field. Test capacity and turn boundaries.
- **Mutagenic Strength:** import without an extra relic field; Artifact and Strength effects are already public. Correct trigger ordering still requires mechanism validation and cannot be inferred merely from Artifact being encoded.
- **Snecko Eye:** conditional import if non-hand effective costs remain unknown and actual drawn hand costs are visible. Existing normalization already distinguishes these cases; randomization and extra draw remain backend-owned and require tests.
- **Velvet Choker:** read authoritative backend counts; existing cards_played_this_turn is exported and used by backend legality. Verify manual/automatic/repeated-play semantics, then reuse that field without duplicating a relic counter. Apply the same backend-first review to other complex counters.
- **Bottled relations:** exact binding is preferred. The backend already has master-deck bottleIdxs and concrete card uniqueId lifecycle; reuse these strictly as internal routing, plus the general Stasis relation/fusion concept. Existing Stasis validation is enemy-to-card specific and must be generalized explicitly. Same-name fallback was conditionally permitted only if exact binding proves complex; no such blocker is established, and ambiguous name matching is not selected.

These are scope decisions and code-inspection findings, not implementation or runtime acceptance. Registered as I11. The existing fixed training pool remains unchanged.


## 8. Implementation follow-through

I12 authorizes execution of these decisions with one progress report per imported relic. The eleven approved imports are implemented in relic-state-v3; see [third batch report](relic-third-batch-report.md) for exact tests, fields and remaining limits. The preceding code-inspection section records the decision-time baseline and is not the latest implementation status. Gambling Chip and the explicit exclusions remain unimported.
