# AGENTS.md — STS1 research workspace

## Current purpose and authority

This is a learning-oriented STS1 Ironclad combat research project. The local folder name `sts2` is historical. The current question is whether the existing Set Transformer + PPO policy improves over its own untrained initialization on the fixed admitted combat distribution. A clear, mentor-readable research snapshot is the immediate delivery goal; proving Set superiority over MLP is not required.

Authority: [spec-v6.md](spec-v6.md), with its dated amendments registered in [docs/decisions.md](docs/decisions.md), then [mechanics](docs/mechanics.md) for resolution order, then [learning objectives](docs/learning-path-v2.md). Do not treat early status tables as current implementation status. Record changes to governing decisions before updating the specification. I6 records the 2026-09-16 framing, language, and cleanup decision; it does not reset the schedule, budgets, or Gates.

Use English for new or substantially revised supported documentation, comments/docstrings, CLI messages, tests, and reports. Existing Chinese technical specifications and historical evidence remain valid during gradual migration; translating the entire tree is not a prerequisite. Conversation language follows the user. Use lowercase kebab-case for document/script names and valid Python naming conventions for Python modules. Do not rename stable schema keys for style.

## Default development path

`scripts/run-a-path-ppo.py` -> `sts/train/apath.py` -> `sts/env/apath.py` -> `sts/env/ironclad.py` / `full_card_public` -> locked C++ backend. The model is `sts/models/apath.py`; the interactive agent is `sts/agents/apath.py`.

Preserve four SAB layers, width 64, four heads, FF128, single-seed PMA, source-then-conditional-target actions, joint log probability/PPO and exact joint entropy. Sample source groups uniformly and shuffle the whole rollout for PPO; content groups are diagnostic categories, not quotas.

The registered pool has 39 deck contents, 33 source groups, two conditions and five encounters (390 configurations). Broader environment support is not training admission. Legacy Unified/Comparison/MLP code remains for compatibility and historical experiments; MLP is frozen to its original comparison scope. Do not compare expanded Set scores directly with frozen MLP scores as an architecture conclusion.

Relic mechanisms and faithful Act 1/2 combat are the next development priority, retained in [pending plans](docs/plans/README.md). I7 requires completion and validation of the agreed reward, potion and required relic-state work before investigating SlayTheData.7z or preparing the new A+B initial-state pool; freeze the resulting contracts and budget before training. A pending plan is not authorization to implement, expand admission, or train. Every required owned relic instance in an admitted scene must be represented with its necessary public state; do not remove unsupported relics merely to admit a scene.

## Execution boundaries

- Preserve user changes, untracked work, ignored experiments, backend patches, and original artifact hashes. Inspect Git state before edits; do not reset, clean, overwrite, or include unrelated work in a commit. Use isolated worktrees for scoped implementation unless the user explicitly selects the current checkout. The documentation cleanup is authorized in the current checkout, with a local commit and no push.
- `eval_seeds.json` is immutable. Evaluation seeds are in `[0,1000)`; training environment seeds are at least `100000`. Record its hash per run. Seeds and hidden randomness are not model features.
- Routing slots identify action instances, not semantic token features. Legal actions come from the environment; apply masks before softmax and use the masked distribution for gradients.
- Within a comparison, preserve information, action semantics, task/split versions, reward, gamma and full real RTG. `battle_reward_v1` and `run_reward_v1` must never be mixed. Reward changes need a new version and recomputation from verifiable fields.
- Legacy battle_reward_v1: zero nonterminal reward, first victory `1 + 0.5 * exit_hp/max_hp`, zero genuine defeat; gamma=1, beta=0. Future run reward applies only to the first final run victory; battle victory cannot terminate a global run. Reject formal run training until RunEnv exists.
- True termination does not bootstrap. External truncation uses the final pre-reset observation for bootstrap; GAE does not cross reset. Exceptions/truncations are not fabricated defeats. Reject unknown required fields rather than inventing zeros.
- Do not expand pools, alter model-facing fields/rewards, launch substantial training, renew a past budget, or push without applicable user authorization. Raise new decisions or critical unresolved questions for the owner to verify; continue independent safe work.
- Keep spec-v6 sections 9/10 schedules and stop rules. Execute the predefined Gate fallback; after three days without progress on one issue, stop and change direction under section 10.3. No new features in weeks 17–18.
- Decompiled sources are for narrow specification arbitration only (D13), never copied into the simulator. Keep proprietary/reference material under ignored `reference/`; do not publish it. Do not create empty scaffolding to imply progress.

## Evidence and navigation

Report implementation, tests, real runtime closure, learning improvement, generalization, and owner understanding separately. Link historical results with their original scope and date. Primary sources are required for game-mechanic and paper claims; label unverified claims explicitly. Preserve the source-log convention (confidence and verification date) illustrated in [the historical source register](archive/research/sts2-a20-decision-model-sources.md).

Use [docs/README.md](docs/README.md) for current navigation and [archive/README.md](archive/README.md) for history. Archived instructions do not authorize new work. Existing source bundles/checkpoints retain their original identities; do not loosen fingerprint checks to make them load. Report what changed, what was checked, and what remains unfinished.

A-path reward amendment I8: battle_reward_v2 uses B=2, alpha=1, lambda=0.05, initial-max-HP-normalized net HP and potion-use cost, paid once at true termination. Preserve legacy v1, external-truncation bootstrap and strict reward fingerprinting.

I9 authorizes scoped relic implementation with one-hot identity, based on I8. Special relic selection/binding/visibility/capacity semantics require owner review; ordinary verified state work may proceed. No new pool admission or substantial training.

I10 records the completed static Act 1/2 relic scope audit and ordinary second batch. The development relic registry is relic-state-v2 (22 one-hot identities plus 3 counter fields). The formal pool remains unchanged; special relic reviews and broader runtime certification are pending.

I13 authorizes the remaining combat-scope imports. The diagnostic registry is now relic-state-v4 (135 one-hot identities plus 6 state fields, raw RELIC width 141). See docs/relic-remaining-report.md; ownership-only run effects do not imply RunEnv support. Formal training admission remains unchanged.

I14/I15 record the initial-state pilot and the separately approved A-v2 experiment. See projects/battle-initial-states/README.md and docs/decisions.md for the current scope. The experiment uses two shared SAB blocks and two blocks per actor/critic branch, preserving four-block path depth, width 64, four heads and FF128. Its versioned 1,715-state corpus and 50/50 natural/augmentation sampler do not replace the legacy 390-configuration pool. The approved run has 262,144 transitions and a four-hour total cap; consolidation does not renew that budget. Preserve the active sts2-initial-states checkout and all launch fingerprints until the run closes.
