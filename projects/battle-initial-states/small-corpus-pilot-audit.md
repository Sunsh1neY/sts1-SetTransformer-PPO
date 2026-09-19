# Small-corpus initial-state pilot: plan audit

Date: 2026-09-19. Status: audit complete; implementation and new admission not performed.

## Verdict

Use the pinned MaT1g3R corpus to establish a reproducible engineering pipeline, then decide whether a bounded investigation of SlayTheData.7z is worthwhile. The direction is sound, but the supplied plan needs changes before execution: it assumes a current frozen schema, treats scoped backend evidence as general readiness, and omits the strict A-path registration boundary.

Retain strict historical reconstruction, independent environment randomness, intact rejection, provenance grouping, coverage reporting and no predetermined A/B ratio. Make the immediate exit gate **pilot pipeline evidence**, not a decision that A is sufficient for broad PPO research. A small-source coverage gap alone cannot distinguish a reconstruction defect from absent source fields or a population gap.

## Audited baselines

- Current checkout: `C:/Users/19091/Desktop/sts2`, `main`, HEAD `9635d2c79c81f55b9985cc5618f516301fafe113`; clean before adding these audit documents.
- Attachment checkout: `C:/Users/19091/Desktop/sts2-relic-state-v1`, HEAD `f626844881a122f619f76e68bab9d415ffdea4ce`.
- Attachment: `docs/a-first-initial-state-dataset-plan.md`, SHA-256 `9f50703739231f8510fabbc80f82d6d6d98af5838addcd9f5fc8268071b87e96`.
- Attachment checkout already contains a modified `docs/act12-relic-audit.md` and the untracked plan. Both were preserved.
- This audit uses current source inspection, a read-only inventory of the cached fixed ZIP, and existing reports as explicitly dated evidence. It does not rerun backend tests or recalculate current admissible-state counts.

## Findings requiring plan changes

### F1 — The claimed frozen schema is not a current integrated contract (high)

Plan sections 1, 6, 11 and 13 call `battle-initial-state-v1` frozen and completed. No matching schema document or active implementation was found in the inspected current/attachment source trees. An older implementation exists under `reference/desktop-repo-archive-20260914/original-directories/sts-worktree-consolidation/sts/data/initial_state.py`.

That archived implementation is not lossless for the current backend:

- `_parse_card` permits only name and upgrade count; it cannot preserve required permanent per-instance card values in that structure.
- `_normalise_cards` sorts cards without a concrete-instance binding remap.
- `_normalise_payload` sorts relic names. Current I12 explicitly defines relic input order as acquisition order; initialization interactions can depend on it.
- `from_candidate` accepts `player.gold` but omits it from the resulting state payload. Gold is part of the current reset input and must be accounted for in the semantic field map.
- The old state keys do not include burning-elite state, and the adapter does not carry it through. It also redundantly stores upgrades despite the new plan's no-redundancy rule.

Required correction: recover the intended schema artifact and compare every semantic field with the current reset contract. If the only reusable implementation is the archived one, preserve its identity and propose a versioned successor rather than silently redefining v1. Do not freeze the name before this comparison. This is a current capability mismatch, not merely a source-format difference.

Validation must establish that provenance/seed/ref renaming does not change semantic identity, while HP, relevant gold, counters, permanent card values, meaningful acquisition order and meaningful bindings do. Deck reordering must remap bindings; do not treat array sorting alone as canonicalization. Equivalent indistinguishable copies require an explicit identity rule.

### F2 — General backend readiness exceeds the available evidence (high)

Plan sections 1 and 13 mark combat/state/Token implementation done without a scope qualifier. `docs/relic-remaining-report.md:41-47` reports 5,865 passing tests and one CUDA deselection, but explicitly distinguishes the 102-by-44 reset/step surface from full episodes and all relic combinations. These are recorded results, not tests rerun by this audit.

Required correction: replace the blanket completion claim with pinned implementation versions and a capability/evidence matrix. Maintain separate columns for source recoverability, schema representability, backend reset, Token/model forwarding, action routing, complete-episode diagnostics and formal training admission. A registered identity is not certification of all reachable interactions. I7 prerequisites require an explicit acceptance check; do not reset the existing schedule or budget.

### F3 — A new corpus cannot directly enter the current A-path sampler (high)

`sts/env/apath.py:28-40` checks the existing pool fingerprint. `scene`/`sample_scene` use its registered contents, profiles and encounters. `APathEnv.reset` at line 77 reconstructs the expected registered scene and rejects anything else. New canonical A records are not a drop-in input.

The diagnostic route through `sts/env/ironclad.py` and `sts/env/full_card_public.py` can support bounded engineering checks, but the latter still carries legacy battle_reward_v1 behavior. Reward v2 wrapping is implemented in APathEnv. Therefore a generic diagnostic reset/step success does not certify the A-path reward-v2 pipeline.

Required correction: specify the adapter and a separate diagnostic validation route using current Token encoders and joint action routing, with explicit v2 reward/termination/truncation checks where claimed. Keep training admission false. Any future registration/sampler integration is a separately reviewed change; do not loosen existing fingerprints, relabel train as diagnostic, or write candidates into the formal pool for convenience.

### F4 — Simulator support does not recover missing run history (high)

The source supports useful prefix reconstruction, but ownership, end-of-run statistics and aggregate counts do not by themselves establish intermediate relic counters, potion inventory timing, exact card bindings or permanent card values. Greater backend coverage removes implementation exclusions, not missing historical evidence.

`scripts/audit-public-corpus.py:26` still has an eight-relic reconstruction whitelist. `scripts/expand-public-prefixes.py` already adds event/shop reconstruction and must also be reviewed for reuse; starting over from the earliest script would discard later work. Both are scoped historical tooling, not a current all-Act-1/2 admission engine.

Required correction: classify exclusions as `source_missing`, `prefix_rule_unimplemented`, `schema_unrepresentable`, `backend_unsupported`, `runtime_failure` or `source_compatibility_unverified`. Preserve first unresolved dependency plus separately detectable additional blockers. Only rule or implementation gaps can be repaired without obtaining new evidence. Do not add a supported relic to a reconstruction whitelist unless its historical required state is also established.

For HP and potions, pin floor indexing and entry timing from verified recorder/rule evidence. Distinguish an empty logged inventory from absent logging. Source-derived potion multisets may use a justified canonical slot mapping only after proving slot equivalence for the supported mechanics; do not claim original slot recovery. Do not substitute `master_deck` for an earlier deck.

### F5 — Small-corpus success is not a large-source sufficiency decision (medium)

Plan sections 8 and 12 jump from A coverage to A-only or B supplementation. Insert the owner's small-source versus large-source decision first.

After the pilot, classify the dominant gap:

| Evidence | Next decision |
|---|---|
| Adapter or prefix implementation is the bottleneck | Fix the bounded pipeline issue; more records will not repair it. |
| Required fields are absent | Seek a demonstrably richer recorder/snapshot source; inspect large-source samples only to test field availability. |
| Valid states exist, but the population is narrow | Consider a bounded large-source sample for incremental independent-state/mechanic yield. |
| The bounded research question is already supported | Consider freezing that scoped corpus; no large archive is required. |

Only then decide whether targeted B is useful. A larger archive is not presumed richer in state fields. Keep B's reachability rationale auditable; rule-valid values alone do not prove joint reachability.

### F6 — Leakage and selection bias need explicit treatment (medium)

Group raw duplicates, play IDs and related source seeds before splitting. In addition, detect identical canonical states across otherwise distinct runs. Choose and document a conservative connected-component or exclusion policy for those overlaps, while reporting original run count, state count and resulting split components separately.

The checked small corpus is entirely A20. Do not downgrade it or infer generalization to other ascensions. The publisher describes streamer histories and curated samples; this is not a random player population. Successful prefix reconstruction may disproportionately retain early/simple states. Report source inventory, reconstructible candidates and runtime-validated subsets side by side, including floor/act-specific attrition. Do not select samples by outcomes or model score. Provisional splits are not the immutable evaluation seed file or a final evaluation protocol.

## Revised pilot sequence and exit criteria

1. **Baseline and prerequisites.** Pin repository/backend binary/patch, registry, reward, Token contract, source ZIP and reconstruction-tool hashes. Confirm I7 prerequisites from scoped evidence. Record the small-source-first decision before future governing specification changes.
2. **Field map and schema.** Document raw field -> historical rule -> canonical field -> reset field -> observed effect. Resolve the archived-v1 conflicts above. Include gold, acquisition order, card bindings, permanent values, potion capacity and conditional burning-elite fields. Unknown required values must fail closed.
3. **Inventory.** Reuse the pinned cached source; parse character fields across all paths. Record aliases, connected groups, source build/logging availability and conflicts. No large archive download is needed.
4. **Bounded reconstruction.** Begin with the simplest fully evidenced real prefixes, then cover additional supported cases. Inventory both acts; an Act 1-only successful subset is a valid pilot result if Act 2 blockers are explicit. Preserve field evidence and rejected candidates. Do not promise nonzero strict historical admission in advance.
5. **Canonical store and split.** Write/read/hash round trips; test semantic changes and equivalent ref/order transformations. Build overlap-safe provisional components. Keep source seed separate from environment RNG and all provenance outside model features.
6. **Runtime closure.** Reset every proposed pilot state and validate Tokens, masks, finite model forward output and legal joint action routing. Run a declared bounded set of complete combat diagnostics covering represented mechanism families. Record actual termination, truncation and exceptions separately; verify claimed reward-v2 calculations from authoritative fields. Fixed state plus seed should reproduce behavior; multiple seeds test reset robustness, not independent source count. Use permitted development seeds >=100000; preserve `eval_seeds.json`.
7. **Pilot report and source decision.** Report stage counts, exact blockers, supported runtime scope, attrition/coverage and reproducibility. Decide whether to stop with the small source, repair extraction, seek richer logs or inspect bounded large-source samples. New training admission, sampling and budget remain separate decisions.

Engineering success requires at least one fully evidenced A record to traverse the complete intended route plus the declared diagnostic coverage. If no state passes strict source admission, deliver a reproducible rejection/feasibility result; constructed fixtures may validate infrastructure but cannot count as successful A admission. A PPO update/checkpoint smoke, if later desired, needs its own explicit scope and cannot be counted as learning improvement.

## Source evidence and checks performed

| Evidence | Result | Confidence / verification |
|---|---|---|
| Cached pinned ZIP | Commit `097aaf3564c2247835162d267cbc7c55d2c9039e`; 9,838,209 bytes; SHA-256 `0b21c5fe489ac0980131d0dd14350efdf1c68f180488b6d2072ae0e81cea565e` | High; bytes rehashed 2026-09-19 |
| Read-only existing loader/grouping functions | 203 Ironclad files, 157 connected groups, 0 conflicting groups, 3,957 whole-run combat records; all 157 groups A20 | High for these functions and pinned source; recomputed 2026-09-19, not current admission counts |
| Existing M2 report | 257 old rule candidates and related coverage counts | Historical only, 2026-09-12; not recomputed as current eligibility |
| Current source / I12 / relic reports | Strict pool gate, required acquisition order and concrete bottle binding; scoped runtime evidence | Source inspected 2026-09-19; runtime report results not rerun |
| [Publisher README at fixed commit](https://github.com/MaT1g3R/Slay-the-Spire-data/blob/097aaf3564c2247835162d267cbc7c55d2c9039e/README.md) | Streamer-run source and Run History Plus usage context | Primary publisher statement, single source; fetched 2026-09-19 using Tavily extract |

Cross-search was attempted through SearXNG, Tavily and Doubao. SearXNG failed to connect; Tavily located the publisher and fetched the fixed README; Doubao did not add usable corroboration. Search results were not treated as independent proof of state recoverability. The source snapshot was verified locally rather than relying on snippets.

No pipeline implementation, backend execution, new formal corpus, learning result, generalization result, owner-understanding assessment, large-dataset acquisition, commit or push was produced in this audit. New files are confined to this project folder; original source artifacts and the supplied plan remain in place.
