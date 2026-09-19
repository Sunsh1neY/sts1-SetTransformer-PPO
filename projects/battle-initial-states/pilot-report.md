# Small-corpus pilot: engineering closure after source audit

> Historical pre-projection snapshot. For the current source-backbone/training-instance split and supported-potion result, see [potion-projection-report.md](potion-projection-report.md).

Date: 2026-09-19. Branch: `codex/battle-initial-states`.
Baseline: `9635d2c79c81f55b9985cc5618f516301fafe113`.
Status: bounded diagnostic pipeline passed; strict historical A admission remains unresolved.

Updated after the [source compatibility audit](source-compatibility-report.md) recovered rows with integer-valued float floors. The original first-closure evidence is preserved by [snapshot manifest](pre-source-audit-snapshot.json).

## Delivered

The owner-approved v2 contract preserves gold, acquisition-ordered relic state and concrete bottle bindings while canonicalizing the deck. Required unknown state is rejected. Unsupported permanent-card input is rejected rather than omitted. V1 and the formal pool are unchanged. Shared simulation/model/reward code was reused without modification.

Implemented source inventory, conservative prefix reconstruction, canonical JSONL storage, connected-source/state-overlap grouping, strict reset adaptation and a bounded validator using `RelicEnv` with the current A-path model, joint routing and battle_reward_v2. All project tools and results are in this folder; governing authorization is recorded as I14 in `docs/decisions.md`.

| Stage | Observed result |
|---|---|
| Pinned source | 203 Ironclad files; 157 connected groups; 46 duplicates; no conflicting groups |
| Source population | 3,957 whole-run combat records; all groups A20 |
| Conservative reconstruction | 251 rule-derived occurrences, 105 source groups |
| Canonical storage | 217 distinct states; stable JSONL round trip and content hashes |
| Leakage grouping | 71 connected components after merging groups sharing identical states |
| Current runtime | 217/217 reset, Token encoding, finite model/value/entropy, normalized joint probabilities and legal action step checks |
| Bounded combat checks | 32 states selected by content-label coverage, two development seeds each; 64/64 true terminations, no exceptions or truncations |
| Reward accounting | Independent terminal formula and action-based potion-use checks passed; 47 potion actions across the 64 episodes |
| Deterministic replay | Two selected states replayed with identical seed/action-generator state; semantic traces and accounting matched |
| Strict historical A admission | **0**; historical build/mod/rules equivalence remains unverified |
| Training | No new pool or distribution, no pilot optimizer updates, no learning/generalization claim |

The untrained diagnostic model produced 50 victories and 14 defeats. These are execution outcomes on coverage-selected cases, not a win-rate estimate, baseline comparison, learned policy result or a reason to select training cases. No held-out evaluation protocol has been established.

## Tests and verification

- Project tests: **47 passed**. Covers lossless round trips, tamper rejection, player fields, relic order/counters, deck permutation with binding remapping, equivalent duplicate cards, source-independent identity, transitive overlap, complete ledger coverage, corrupt source rejection, numeric source-floor joins and certification boundaries.
- Focused existing reward/relic regressions in the preceding pilot pass: **160 passed, 4,590 deselected**. Command: `python -m pytest tests/test_battle_reward_v2.py tests/test_relic_remaining.py -k 'not act12_reset_step_surface and not forward' -q`. These include existing bounded PPO checkpoint/update regression tests; they do not create a new training experiment or budget. No environment code changed during the subsequent source audit, so those regressions were not rerun.
- Source ZIP hash, actual imported backend binary and pinned implementation hashes were checked. The backend binary matches the recorded main integration hash `70f3d9e128c71deec13b30faf8128189635203da8261e7d937b279cba2c93924`.
- Evaluation seeds, formal pool, relic registry and backend patch still match the integrated baseline.
- The original 204-state corpus hash was `411bc8c72ed334a26ffb2511f85a33319073530899aa928f375d0dc653efe1cb`; it is preserved in the historical snapshot. After fixing integral-float source-floor lookup, the 217-state corpus hash is `bd769577bce58d2adf6a470ea65403b195ff742a36f7a01ccfab42ea878172d5`.
- The initial runtime pass was rerun after tightening missing-counter/permanent-card validation. Final evidence references the tightened implementation. A Windows GBK decoding failure in the ledger test was corrected with explicit UTF-8; the final suite passed.

For exact commands, code, manifests and machine-readable results, see [README](README.md). Both runtime seeds are >=100000. `eval_seeds.json` was not used as a convenient development seed source or changed.

## Coverage and material limits

The 217-state corpus covers 14 ordinary Act 1 encounter labels, six relic identities, 15 potion identities and 68 card-plus-upgrade labels. Deck sizes range from 9 to 15. The 251 source occurrences are on floors 1, 2, 3, 4, 5, 7 and 8. There are no admitted Act 2 prefixes, elite encounters or demonstrated persistent-counter/bottle source states in this pilot.

The 32 full-combat representatives cover every encounter/relic/potion identity present in the pilot. Five card labels occur elsewhere in the corpus but not in this complete-combat subset: Defend_R+1, Dual Wield, Ghostly Armor, Offering and Pummel. All 217 still passed the one-step check. Identity occurrence is not proof that every effect or interaction was exercised. Bottle semantics have dedicated canonicalization tests but are not exercised by these source-derived episodes. There were no runtime truncations in the selected episodes; truncation accounting is supported by the focused existing regressions, not by a newly observed truncation in this corpus.

The prefix engine deliberately reuses conservative historical rules, including the old eight-relic recoverability restriction. It is not a claim to maximize current recoverable A. Current card/relic/encounter lists are used for content checks; the obsolete True Grit+ secondary-choice exclusion is removed in the local adapter because that routing already exists. Existing event/shop reconstruction is reused. No original historical script/output was overwritten.

The complete ledger includes all 3,957 records, including out-of-scope records and failures. Representative first-listed exclusions include:

| Reason | Combat records | Interpretation |
|---|---:|---|
| Outside Act 1/2 scope | 1,366 | Whole-run source includes later acts; not a pilot defect |
| Prefix floor rule not implemented | 1,309 | Existing helper is restricted to Act 1 floors 1-15; not proof that source data is absent |
| Relic history pending | 589 | Conservative prefix dependency; requires per-relic reconstruction evidence |
| Missing elite burning condition | 69 | Source evidence unresolved; cannot insert false |
| Potion automatic use/generation pending | 62 | History reconstruction/ordering not established |

Counts here are the first listed blocker per rejected row, not a complete causal attribution. The ledger also retains all detected blockers and the first recorded blocked prefix transition where available. `source_or_rule_evidence_unresolved` is intentionally unresolved until an example-level audit distinguishes missing logs from an unimplemented proof.

## Source admission remains a separate gate

All 157 groups contain Neow and per-floor potion-use/discard log fields. Only 106 contain `relic_stats`, and 46 contain `basemod:card_modifiers`. Field presence, endpoint nulls and recorder-source compatibility do not prove the exact historical mod/rules setup. The inherited reconstruction output explicitly marks historical rules equivalence unverified; this pilot preserves that label.

Thus the route is closed for **rule-derived diagnostic candidates**. The audit's stronger acceptance requirement of a fully evidenced historical A state is not yet met. Do not relabel these candidates, silently remove the compatibility gate, or register them in the formal training pool.

## D2: Selected and completed source audit

The owner selected the recommended bounded source-compatibility audit. It is complete: [source/build matrix, evidence, raw Act 1/2 coverage and deck completeness](source-compatibility-report.md). All 157 groups remain historically unverified; none was newly certified. The numeric source-floor repair increased the diagnostic corpus from 204 to 217 states without relaxing that gate.

Next useful engineering work is to expand the small-corpus prefix rules and ordinary relic history with independently verified transitions while retaining the same unverified-source boundary. This improves diagnostic coverage but does not by itself clear historical A admission.

Large-source acquisition and processing remain deferred. No evidence from this pilot shows that SlayTheData contains the missing fields. Any later sample investigation should ask that question before bulk processing. No B construction is justified solely by these first conservative counts.

## Remaining work

Source compatibility/admission decision; targeted recoverability improvements (including Act 2); expanded interaction/threshold coverage where source evidence permits; a final research distribution and evaluation protocol; separately authorized training. Owner understanding was not assessed in this implementation pass.

This work is uncommitted in the isolated worktree. No merge, push, large archive download or modification to the original attachment was performed.
