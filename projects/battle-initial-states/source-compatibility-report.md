# Source compatibility and Act 1/2 coverage audit

Date: 2026-09-19. Status: bounded audit complete; historical source certification unresolved.
Scope: the pinned MaT1g3R source and existing recorder evidence, not SlayTheData.7z.

## Findings

The raw corpus contains both Act 1 and Act 2 histories and a run-end master-deck list for every one of the 157 independent groups. It does not supply a complete pre-combat state snapshot for each fight. Current reconstruction remains a conservative Act 1-prefix implementation, even though later-act records exist in the source.

The examined metadata supports identifying four game build strings, matching recorder field families and excluding some explicitly declared nonstandard modes. It does not establish exact historical recorder/mod installation or complete rule equivalence with the locked simulator. All 157 groups remain **unverified**, rather than proven incompatible. No strict historical A state was newly certified.

The audit also found and fixed an actual project-adapter defect: 128 combat rows encode integer-valued floors as JSON floats. Existing prefix code normalizes those numbers to integers; the pilot's scene lookup previously used the unnormalized form (`floor-1.0` versus `floor-1`). A shared lossless numeric normalizer now joins both forms while rejecting booleans, strings, fractional values and nonfinite values. This recovered 18 candidate occurrences and 13 distinct states without changing source admission rules.

## Raw history versus reconstructed state

Counts use the repository's standard floor bands. They describe observed combat entries, not completeness of every room, every possible encounter or every run's two full acts.

| Observed floor band | Groups with at least one combat | Combat records |
|---|---:|---:|
| Act 1, floors 1-17 | 157 | 1,430 |
| Act 2, floors 18-34 | 140 | 1,161 |
| Act 3, floors 35-51 | 115 | 1,165 |
| Floor 52 onward | 101 | 201 |
| Whole source | 157 distinct groups | 3,957 |

Group counts overlap across acts and must not be summed. Early-ending runs do not have the later fights. The current helper considers Act 1 floors 1-15; it does not reconstruct the 148 Act 1 combat records on floors 16-17 or the 1,161 Act 2 combat records. These 1,309 rows are classified as an unimplemented prefix-floor path, not missing raw data.

All 157 run-end `master_deck` fields are nonempty lists of card strings, with 11-48 entries and 157 distinct final multisets. Duplicate cards and explicit upgrade suffixes are preserved. Across them there are 115 base card identifiers, including cards outside the ordinary Ironclad card set; this is not a claim that every game card is covered or supported by the simulator.

The final deck is not an earlier entry deck. One directly traced example is `runs/lose-all-gold-max-hp-sample/IRONCLAD/1672867344.run`: its reconstructed floor-1 deck has 11 cards, while its final `master_deck` has 23. The source group, raw path and canonical hash are recorded in `source-compatibility.json` under `entry_vs_final_deck_example`.

Each retained pilot state includes its complete reconstructed master deck, not a selected subset of that deck. If a required card/value or prefix transition is unresolved, the candidate is excluded intact. This property does not certify all historical runs or recover all earlier decks.

## Source/build matrix

Groups are attributed to their representative source path after the pinned duplicate/identity grouping. All eight rows have recorder field-family evidence; none has a verified run-linked installation manifest.

| Source collection | Recorded build | Independent groups | Historical rule equivalence |
|---|---|---:|---|
| 200-rotating-sample | 2022-03-07 | 8 | Unverified |
| 200-rotating-sample | 2022-10-04 | 26 | Unverified |
| 200-rotating-sample | 2022-12-01 | 13 | Unverified |
| 200-rotating-sample | 2022-12-18 | 3 | Unverified |
| chegs | 2022-12-18 | 46 | Unverified |
| lose-all-gold-max-hp-sample | 2022-12-18 | 10 | Unverified |
| panacea-ironclad-sample | 2022-03-07 | 19 | Unverified |
| panacea-ironclad-sample | 2022-10-04 | 32 | Unverified |

The raw run timestamps span September 2022 to February 2024. A build string is not a recorder version. In particular, the chegs runs retain the December 2022 build string while their recorded run timestamps are in February 2024.

All groups declare daily/endless/trial/beta false, ascension mode true and ascension 20. All also contain `is_prod=false`; this audit records that flag without treating it as proof of changed mechanics or of vanilla equivalence. There are 87 recorded victories and 70 defeats; neither outcome was used to choose certification or reconstruction cases.

Only the 46 chegs groups have `basemod:card_modifiers`; their recorded endpoint entries are all null. The other 111 lack that field. Null endpoint modifiers cannot certify absence of historical modifiers, and absence of the field cannot be converted to an empty list. None of the inspected records contains a complete installation manifest among the inspected metadata fields; metadata-key inventories are saved per group.

## Recorder evidence and its limits

The existing fixed RunHistoryPlus ZIP matches SHA-256 `4272eb2dec27d613f356bfa0f2df21358cef9a00a5fda54de3db76a177425cf3`. Four extracted Java files were byte-compared with that archive. GitHub commit metadata was fetched directly and confirms commit `99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b` dated 2022-09-08, before the earliest run timestamp in this corpus. This supports temporal availability of those logging hooks, not proof they were the exact installed version.

| Evidence | What is supported | What remains unknown |
|---|---|---|
| Publisher's fixed README | Streamer histories and Run History Plus usage context | Exact mod manifest for an individual run |
| Neow logging patch | Logging of selected result identities and HP/gold changes | Whether all historical installations executed identical code |
| Potion logging patch | Floor-indexed use/discard/acquisition logs | Original slots and a total event order sufficient for every ambiguous floor |
| Improvable-card patch | Permanent values are collected from the final master deck at `gatherAllData` | Earlier entry values and persistent card-instance history |
| Green-key patch | Key-claim floor is logged | Every elite's burning flag and enhancement |

The raw `relic_stats` field occurs in 106 groups, and inspected examples contain aggregate-like relic entries and `obtain_stats`. Its detailed per-field semantics were not certified in this bounded audit. No aggregate was substituted for a battle-entry counter and no exact bottle binding was inferred from a name-only value.

Primary source register (verification date 2026-09-19):

- [Publisher README at fixed commit](https://github.com/MaT1g3R/Slay-the-Spire-data/blob/097aaf3564c2247835162d267cbc7c55d2c9039e/README.md): high confidence for the publisher's statement; single primary source. Direct page and cached archive checked.
- [Recorder commit metadata](https://api.github.com/repos/modargo/RunHistoryPlus/commits/99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b): high confidence for commit date; response saved under ignored `reference/battle-initial-states/source-compatibility/recorder-commit.json`, SHA-256 `a12d75e49970c199b0fc7a8f36b380a006a829c1c6656678a3cc3ae6db2e37d3`.
- [Neow patch](https://github.com/modargo/RunHistoryPlus/blob/99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b/src/main/java/runhistoryplus/patches/NeowBonusRunHistoryPatch.java): high confidence for the inspected logging hooks; pinned cached source.
- [Potion patch](https://github.com/modargo/RunHistoryPlus/blob/99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b/src/main/java/runhistoryplus/patches/PotionRunHistoryPatch.java): high confidence for the inspected logging hooks; direct page and pinned cached source.
- [Permanent-card patch](https://github.com/modargo/RunHistoryPlus/blob/99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b/src/main/java/runhistoryplus/patches/ImprovableCardRunHistoryPatch.java): high confidence for final-value timing; direct page and pinned cached source.
- [Green-key patch](https://github.com/modargo/RunHistoryPlus/blob/99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b/src/main/java/runhistoryplus/patches/GreenKeyTakenRunHistoryPatch.java): high confidence for key-claim timing; pinned cached source.

SearXNG could not connect; Tavily search/extract returned a closed transport; Doubao completed searches but supplied no usable certification evidence. Known primary URLs were opened directly. No third-party snippets were used to certify game-version equivalence.

## Corrected pilot evidence

After preserving 12 previous artifacts byte-for-byte under ignored `reference/battle-initial-states/pilot-before-source-audit/`, reconstruction was rerun with the numeric join fix. [The snapshot manifest](pre-source-audit-snapshot.json) preserves their original hashes, including the old 204-state corpus and runtime report.

- 251 rule-derived occurrences from 105 source groups; 217 canonical states; 71 overlap-connected components.
- All 204 prior canonical state identities remain present; 13 new ones were recovered.
- 217/217 reset/Token/model/joint-route checks passed. The updated 32-state coverage selection across two development seeds produced 64 true terminal episodes, zero failures and zero truncations.
- Reward recomputation passed, including 47 explicit potion uses; two same-state/same-seed replay checks passed.
- The untrained model's 50 victories and 14 defeats are diagnostic outcomes, not performance evidence.
- Project tests: **47 passed**, including the float/integer scene-join regression and no-certification-from-metadata tests.

No mechanism, reward, model-facing field, formal pool, evaluation seed or admission policy changed. The corpus hash changed because omitted valid numeric encodings were recovered; provisional connected-component partitions were recomputed rather than treating old provisional assignments as a fixed evaluation protocol.

## Remaining work and next step

The bounded compatibility audit is complete. The unresolved certification requires evidence absent from the inspected material: run-linked recorder/mod versions, trustworthy game-rule/version mapping, and any necessary installation artifacts or equivalent historical documentation. A newer recorder source checkout alone cannot supply this.

There is still useful small-corpus engineering work before large-archive processing: recover ordinary relic prefixes with sufficient logged state, then implement Act 1 boss/Act 2 transitions with exact deck/HP/relic/potion semantics. Keep resulting states diagnostic until the source-evidence gate is resolved. No source assumption was approved or silently relaxed in this pass.

Do not infer that SlayTheData contains richer fields or that more runs would repair these exact evidence gaps. No large archive was downloaded, no B states constructed, and no training was launched.
