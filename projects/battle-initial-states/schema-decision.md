# D1: Pilot schema version and semantic boundary

Status: recommended v2 option approved by the owner on 2026-09-19; implementation and bounded diagnostic validation passed. Historical A source admission remains pending.

## Recommended choice

Introduce `battle-initial-state-v2` as a project data contract. Preserve archived v1 and all historical hashes. This does not change model fields, the backend or formal training admission.

Store character, ascension, act, floor, both entry-timing markers, player HP/max HP/gold, a complete deck with upgrades, acquisition-ordered relic instances with their required persistent state, exact bottle-to-card bindings, complete potion inventory, and conditional burning-elite state. Keep provenance, evidence, splits and environment seeds outside semantic state. A missing required value is an exclusion, never an inferred zero.

Canonicalization treats the deck as an unordered multiset with binding labels attached to the bound card instance. Sort cards by their semantic content and binding labels, then remap bottle indices to canonical indices. Equivalent identical copies with the same state are interchangeable; binding to a different card type, upgrade or permanent state changes identity. Preserve relic acquisition order conservatively; do not sort relics. Preserve supplied potion slots initially; a separately evidenced source adapter can canonicalize a recoverable inventory without claiming historical slots.

Current backend reset accepts card strings with upgrades, not arbitrary permanent per-card values. Reject such unsupported states intact in this pilot. The schema must not imply that representing an identifier or an unimplemented permanent value makes it executable. Burning elites likewise remain unsupported by the current backend even if the source proves the flag.

Tests required before freezing: round-trip identity, no provenance/seed contribution, meaningful gold/counter/binding/order distinctions, deck permutation plus binding remap invariance, unknown-field rejection and no loss of required fields through reset adaptation.

## Alternative

Run a deliberately narrow first pilot using existing reset-scene records, limited to states requiring no special binding or permanent card input, with gold and acquisition order preserved. Defer a canonical v2 corpus until after this narrow runtime feasibility check. This gives an earlier diagnostic but leaves the canonical-store stage incomplete.

## Existing runtime route discovered during implementation preparation

`sts/env/relics.py::RelicEnv` already inherits `APathEnv.step`, initializes `BattleRewardV2`, validates relic fingerprints and enforces development diagnostics. Reuse it for the pilot rather than introducing a new environment or bypassing the formal A-path pool. The earlier audit correctly identified the formal pool boundary, but did not identify this existing v2 diagnostic route; that adapter work is therefore smaller than originally anticipated.

## Field evidence map

| Canonical requirement | Source / derivation to verify | Existing reset target | Pilot rejection boundary |
|---|---|---|---|
| Character / ascension | `character_chosen`, `ascension_level` | `character`, `ascension` | Unknown or incompatible source rules |
| Act / floor / encounter | Combat floor and verified encounter mapping | `act`, `floor`, `encounter` | Do not infer elite flags or conflate event fights |
| Entry timing | Recorder floor-boundary semantics | `entry_timing`, `initialization_phase` | No post-initialization snapshot relabeling |
| HP / max HP / gold | Neow plus verified prior-floor boundaries and prefix transitions | `player` | Never use post-combat values as entry values |
| Master deck / upgrades | Starting deck plus verified acquisition/removal/upgrade prefix | `deck` string array | No substitution of final `master_deck`; unsupported permanent values rejected |
| Relic ownership/order | Starting relic, ordered acquisition and replacement prefix | Ordered `relics` | Ambiguous order or unsupported owned relic rejects intact |
| Persistent counters | Sufficient historical transitions or explicit boundary snapshot | `{name, counter}` | Aggregate final `relic_stats` is not an entry counter |
| Bottle binding | Exact selected card instance, tracked through modifications | `{name, card_index}` | Card name alone is insufficient when instances differ |
| Potions | Acquisition/use/discard logs with proven timing | `potions` slots | Absent logs, ambiguous generation/use and unsupported capacity rejected |
| Burning elite | Explicit evidence or rule-backed exclusion | `burning_elite` | Missing elite condition and true burning flag both block current runtime |

This proposal is reviewable without selecting a training pool, sampling weights or a training budget.
