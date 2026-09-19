# Reconstruction engine plan

Date: 2026-09-19
Scope: STS1 Ironclad public-run reconstruction, A-path diagnostic preparation
Status: planning and contract-reconciliation proposal; implementation not started in the main checkout

## 1. Decision

It is appropriate to start the reconstruction-engine work as a bounded
organization and contract-freezing effort. The newly added source-to-backend
projection makes the correct engine boundary clearer: preserve the complete
source backbone, then derive a separately identified executable instance under
an explicit projection policy. It is not yet appropriate to start another
parallel implementation, expand the formal A-path pool, process
`SlayTheData.7z`, generate B scenes, or launch PPO.

The current pilot has already demonstrated enough useful structure to justify
an engine boundary: source inventory, connected source groups, prefix-derived
candidates, canonical state hashing, blocker ledgers, runtime validation and
coverage reports. The current work is still a pilot, however, and the active
implementation checkout is not a stable release baseline.

## 2. Repository and worktree situation

- The linked Codex task is **“审计 MaT1g3R 数据集计划”**.
- Its local project is `C:\Users\19091\Desktop\sts2`, project label `sts2`,
  on the local host.
- The main checkout is currently on `main` at `9635d2c` with the existing
  untracked `projects/` directory. This plan is the only new artifact added by
  this document pass.
- The active implementation is in the separate worktree
  `C:\Users\19091\Desktop\sts2-initial-states`, branch
  `codex/battle-initial-states`. It has dirty tracked changes in
  `docs/decisions.md`, `scripts/audit-public-corpus.py` and
  `scripts/expand-public-prefixes.py`, plus untracked project artifacts.
- The linked task is still active. Do not merge, reset, clean, overwrite or
  reinterpret that worktree while it is still producing its final report.

The active worktree has already produced the following useful pilot components:

- `initial_state.py`: strict canonical-state validation and hashing;
- `reconstruct-pilot.py`: source-group reconstruction and candidate ledger
  generation;
- `audit-source-compatibility.py`: source/build compatibility evidence;
- `validate-runtime.py`: reset, observation, Token, model, route and bounded
  episode checks;
- machine-readable candidate, blocker, coverage, runtime and corpus reports.

The generated baseline is now represented by multiple explicit snapshots. The
pre-projection report records 585 backend-validated instances; the latest
projection report records 2,292 source backbones, 1,406 scope-projected
occurrences, 1,377 backend-validated instances and 64/64 bounded terminated
rollouts. Earlier 217/558 intermediate outputs remain historical worktree
artifacts. These numbers must not be merged into one count. The first engine
milestone must produce one reproducible snapshot from one source/tool/backend
fingerprint and one named projection policy.

## 3. Research boundary

The engine's purpose is:

> Given a pinned public run source, produce an evidence-carrying, deterministic
> record for every combat-entry attempt: either a canonical diagnostic state
> with its evidence chain, or a rejection with the earliest causal blocker and
> any additional detected blockers.

The engine is not intended to:

- reproduce hidden RNG, pile order or internal state that the source does not
  expose;
- claim exact historical replay when only a visible or rule-derived prefix is
  available;
- turn backend executability into historical source certification;
- change the current A-path model, reward, action semantics, evaluation seeds
  or formal training pool;
- create artificial B scenes;
- decide whether the large archive is richer before a bounded sample audit;
- convert reconstructed states into PPO on-policy trajectories.

The following statuses must remain separate throughout the project:

1. source parses and belongs to a connected source group;
2. the prefix is historically/rule sufficiently evidenced;
3. the state is representable by the canonical schema;
4. the state is executable by the current diagnostic backend;
5. a bounded complete combat diagnostic terminates correctly;
6. source build/mod/rules equivalence is certified;
7. the state is admitted to the formal A-path training distribution.

The current pilot has evidence for stages 1, 3, 4 and bounded portions of 5.
Stage 6 remains unverified in the pilot, and stage 7 remains false.

## 4. Target architecture

The future engine should have one directional dataflow:

```text
raw archive
  -> source adapter and strict parser
  -> connected source groups
  -> ordered run timeline
  -> prefix reducer with explicit transition evidence
  -> source candidate/backbone + evidence chain
  -> canonical source-backbone store
  -> versioned scope projection
  -> backend/training instance store
  -> overlap-safe provenance/split grouping
  -> diagnostic backend adapter
  -> runtime validator
  -> coverage, blocker and reproducibility reports
```

The key separation is between a **reconstruction core** and a **research
adapter**:

### Reconstruction core

This layer knows about source fields, run/floor events, reconstruction rules,
evidence and canonical state identity. It must not import the PPO trainer or
silently call the formal sampler.

Its stable domain records should be conceptually equivalent to:

- `RawRun`: immutable source bytes, parser version and source metadata;
- `SourceGroup`: duplicate/related-run component and conflict status;
- `TimelineEvent`: floor-boundary event with source location and confidence;
- `CandidateOccurrence`: one source combat occurrence, not yet deduplicated;
- `CanonicalInitialState`: semantic state only;
- `EvidenceChain`: field-level derivations and unresolved dependencies;
- `Blocker`: machine-readable reason, category, first occurrence and impact.

### Scope projection boundary

Projection is a first-class engine stage, not a reconstruction rule and not a
silent filter. The current `supported-potions-only-v1` implementation provides
the intended shape:

- `source_backbone` retains the complete source-observed potion inventory;
- `source_backbone_hash` identifies that source-derived semantic state;
- `state` is the current backend-executable instance;
- `state_hash` identifies the projected executable state;
- `potion_projection` records policy, source inventory, removed identities,
  counts, preserved capacity, replacement behavior and registry changes.

The projection may remove an unsupported source potion from the executable
instance while preserving an empty slot. It must never replace it with another
potion, expand the backend registry, remove Potion Belt or unsupported cards to
make a row executable, or rewrite the source backbone. A projection can change
action availability and therefore changes the executable distribution; it must
be reported as a separate stratum and must not be called an exact historical
state.

The durable engine contract should additionally give every projection result a
`projection_policy_id` and a projection-manifest hash. This prevents a future
policy from being mistaken for the same executable corpus merely because the
resulting `state` happens to have the same hash.

### Research adapter

This layer converts a canonical diagnostic state into the existing current
backend reset interface and runs the declared validation chain. It records
backend, Token, model-forward, mask/route, termination, truncation, exception
and reward-accounting evidence without changing the state identity.

The adapter may reuse `RelicEnv`, `APathEnv`, the current Token encoders and
the current joint action route. It must not write new states into the formal
training pool merely because they pass a diagnostic reset.

## 5. Contract that must be reconciled before extraction

The first implementation milestone is not a new reconstruction rule. It is a
contract audit with a golden snapshot.

### Canonical semantic contract

The proposed v2 state should preserve, at minimum:

- character and ascension;
- act, floor, encounter and explicit entry timing;
- player HP, max HP and gold;
- the complete deck with upgrades and any representable instance state;
- acquisition-ordered relic instances and required counters;
- exact bottle-to-card instance bindings;
- complete potion inventory under an explicitly documented slot policy;
- explicit burning-elite state when the source proves it.

Unknown required values must reject the candidate. They must not be replaced by
zero, a default counter, a guessed encounter or the final run `master_deck`.

### Drift to resolve

The current pilot contains an important version mismatch:

- `initial_state.py` defines `battle-initial-state-v2` as the strict canonical
  record version;
- `reconstruct-pilot.py` emits a `small-corpus-reconstruction-report-v1`
  summary;
- `build-a-corpus.py` currently emits rows labelled `battle-initial-state-v1`
  inside a backend-validated project artifact.

Before engine extraction, decide explicitly whether these are:

1. one v2 semantic state with separately versioned report/envelope schemas; or
2. two intentionally different state contracts with a declared migration.

The engine must not leave this as a filename or producer-dependent convention.
The same pass must define the meaning of `diagnostic`, `backend-validated`,
`source-certified` and `training-admitted`. In particular, an artifact called
“admitted” must not be ambiguous when `training_pool_admitted` is false.

The projection adds one more required distinction:

| Layer | Identity | Meaning |
|---|---|---|
| Source backbone | `source_backbone_hash` | Complete source-derived semantic state; no backend projection applied |
| Executable instance | `state_hash` | State sent to the current backend after a named projection/configuration policy |
| Projection policy | `projection_policy_id` + manifest hash | The transformation that connects the two layers |

The current focused state/projection/version test set passed 26 tests in the
active worktree. This is useful contract evidence, not a full repository
regression or formal training evidence.

## 6. Blocker model

Every rejected combat occurrence should contain:

- `first_blocker`: the earliest dependency that breaks the historical state
  chain;
- `additional_blockers`: other independently observed problems;
- `category`;
- source group, floor, room/encounter and source location;
- whether the blocker is repairable in code, requires richer source evidence,
  requires a backend change, or needs owner review;
- estimated downstream release: number of later occurrences and source groups
  that could be unlocked by fixing it.

The initial category vocabulary should be stable and small:

- `out_of_scope`;
- `source_missing_or_ambiguous`;
- `prefix_rule_unimplemented`;
- `schema_unrepresentable`;
- `backend_unsupported`;
- `runtime_failure`;
- `source_compatibility_unverified`;
- `parser_or_schema_error`.

The engine should retain raw reason codes such as relic-history, potion-timing,
burning-elite, floor-rule, permanent-card-state and secondary-choice blockers.
It should not collapse them into a generic `failed` label.

## 7. Phased build plan

### Phase 0 — Freeze the pilot snapshot

Do this before any refactor.

Deliverables:

- the active task's final status and exact worktree diff;
- one pinned source archive hash, backend hash, registry hash, tool hash and
  Python/dependency fingerprint;
- a manifest of every generated ledger/report/artifact and its hash;
- one reproducible command sequence from raw source to report;
- explicit separation of the earlier and latest generated snapshots.

Exit criteria:

- the active task is no longer changing the outputs;
- the selected snapshot can be regenerated without changing counts or hashes;
- no merge or training decision is hidden inside the snapshot step.

### Phase 1 — Reconcile contracts and establish golden fixtures

Deliverables:

- field map: raw field -> rule/derivation -> canonical field -> reset field ->
  evidence requirement;
- explicit v2 state schema and envelope/report schemas;
- migration or rejection policy for every v1 artifact;
- small golden fixtures for deck permutation, bottle binding, relic order,
  persistent counters, gold, potion capacity, burning-elite state and unknown
  values;
- an invariant that provenance, source seed and environment seed do not enter
  semantic `state_hash`.

Exit criteria:

- canonical round-trip and hash identity are stable;
- meaningful state changes change the hash;
- equivalent deck permutations with remapped bindings do not change the hash;
- unsupported permanent card values and missing required counters reject intact.

### Phase 2 — Extract the reconstruction core without changing behavior

Move behavior from the current pilot scripts into a project-local package only
after Phase 0 and Phase 1. The intended conceptual modules are:

```text
engine/
  contracts.py       # schema and versioned envelopes
  sources.py         # archive parsing and source grouping
  timeline.py        # ordered floor/room event view
  rules/             # one rule family per transition type
  candidates.py      # occurrence creation and rejection
  canonical.py       # normalization, state hash, record IO
  provenance.py      # overlap components and split metadata
  blockers.py        # first-cause and additional blockers
  runtime.py         # diagnostic adapter boundary
  reports.py         # deterministic machine-readable summaries
```

This is a target structure, not permission to create empty scaffolding. Each
module should be introduced only with behavior, tests and a before/after
artifact comparison.

The first extraction should reuse and then retire the implicit coupling where
`reconstruct-pilot.py` imports `scripts/expand-public-prefixes.py` and replaces
one of its blocker functions at runtime. Such monkey-patching is useful for a
pilot experiment but is not a durable engine contract.

Projection functions should be extracted as pure, downstream transforms with
an explicit input/output type. A projection must be idempotent under its own
policy, preserve the source backbone, and expose a deterministic transformation
record. This lets the engine answer both “what did the source contain?” and
“what did the backend receive?” without conflating the two.

Exit criteria:

- the engine reproduces the Phase 0 ledger byte-for-byte or records an
  explicitly reviewed, explained versioned delta;
- no shared `sts/` environment, model, reward or formal pool code was copied;
- all new behavior has focused tests and a deterministic CLI.

### Phase 3 — Add rule families by release, not by whitelist expansion

Implement one evidence-backed rule family at a time, retaining the same
canonical contract and blocker semantics:

1. floor indexing and ordinary Act 1/2 room transitions;
2. deck acquisition/removal/upgrade/transform transitions;
3. ordinary relic acquisition, order and persistent-state transitions;
4. potion acquisition/use/discard/automatic-generation timing;
5. shop and event transitions;
6. permanent card values, bottle bindings and burning elites only when the
   source and backend both support the required semantics;
7. multi-combat and Act 2 continuation.

Each release must report newly unlocked occurrences, source groups, floors and
mechanism labels. A rule is not considered complete because it increases a
count; it needs an evidence fixture, rejection counterexample and downstream
runtime check.

### Phase 4 — Canonical corpus, overlap and split layer

Produce three intentionally different artifacts:

- the complete occurrence ledger, including rejected rows;
- the deduplicated canonical diagnostic corpus;
- the connected source/state components used for leakage-safe analysis.

Keep source group count, occurrence count, canonical state count and component
count separate. Do not count environment seeds as new source states. Report
Act/floor/encounter attrition and the A20-only population explicitly.

### Phase 5 — Runtime validation layer

For every proposed diagnostic state, run the declared chain:

```text
schema validation
  -> current reset adapter
  -> public observation
  -> Token encoding
  -> finite Set Transformer forward/value/entropy
  -> legal masked joint action route
  -> next observation
```

For a coverage-selected subset, add complete combat diagnostics with separate
counts for true termination, external truncation, exception and defeat/victory.
Check reward-v2 accounting independently. A successful untrained rollout is
runtime evidence only; it is not a learning result or a source-certification
result.

### Phase 6 — Coverage and decision report

The final report should answer, with one snapshot and one hash manifest:

- what source records were inspected;
- how many occurrences reached each stage;
- what floors, acts, encounters, cards, relics, counters and potions are
  actually represented;
- which blockers dominate and what one repair could unlock;
- which states are only rule-derived diagnostics;
- whether the small corpus is sufficient for the bounded engineering question;
- whether a richer source sample is justified;
- whether targeted B is justified.

No formal A-path admission follows automatically from this report.

## 8. Immediate next actions

The safe order for the next work session is:

1. Let the active reconstruction task finish its final report; do not touch its
   dirty worktree.
2. Capture one snapshot manifest and choose the final pilot output as the
   golden baseline. Keep the 585 pre-projection and 1,377 post-projection
   snapshots as separate historical artifacts.
3. Freeze `source_backbone`, projected `state`, `source_backbone_hash`,
   `state_hash` and the projection policy/manifest as one contract.
4. Perform the v1/v2 and artifact-status reconciliation described in Phase 1.
5. Write the field map and blocker taxonomy before adding any new historical
   rule.
6. Extract only the minimal core needed to reproduce the frozen pilot output.
7. Re-run focused project tests and the bounded runtime validator.
8. Review the resulting engine plan and evidence with the owner before any
   Act 2 expansion, large-archive sample, B construction, formal pool change or
   training decision.

## 9. Completion definition for “the engine is built”

The reconstruction engine is complete for a declared scope only when all of
the following are true:

- one pinned source and toolchain can reproduce the machine-readable ledger;
- every accepted record has a canonical state, state hash, source group,
  field-level evidence and explicit admission status;
- every rejected occurrence has a first blocker and retained raw reason codes;
- canonicalization is lossless for the declared state semantics and rejects
  unknown required values;
- source provenance, overlap and split components are explicit;
- runtime validation is a separate reproducible stage with its own report;
- coverage and attrition are reported by act/floor/encounter/mechanism;
- historical certification, backend validation and formal training admission
  are not conflated;
- the formal A-path pool, reward, model, evaluation seeds and PPO budget remain
  unchanged unless a later decision explicitly changes them.

Until those criteria are met, the correct label is **pilot reconstruction
pipeline** or **diagnostic corpus**, not a finished historical reconstruction
engine or a training dataset.

## 10. Source documents

- [Small-corpus pilot audit](small-corpus-pilot-audit.md)
- [Project README](README.md)
- [Current governing decisions](../../docs/decisions.md)
- [Current pending-work ordering](../../docs/plans/README.md)
- Active implementation worktree: `C:\Users\19091\Desktop\sts2-initial-states`
