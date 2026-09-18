# Pending work

Status: current roadmap, updated 2026-09-19. Authority remains [spec-v6](../../spec-v6.md), with [decision I6](../decisions.md#i6-clear-research-starting-point-and-bounded-documentation-cleanup-2026-09-16). See also [decision I7](../decisions.md#i7-defer-ab-initial-state-preparation-until-mechanism-and-reward-work-is-complete-2026-09-18) for the required ordering. Plans describe intended work, not completed support or blanket execution authorization.

## 1. Clear starting point — completed

The first-pass cleanup was completed in local commit `3a56708`; see the [completion report](../repository-cleanup-report.md). Its scope was to make the current question, implementation, evidence and next steps easy to find. Archive obsolete instructions, preserve source identity, and repair verified document-path dependencies. Existing technical Chinese material can remain; no parallel Chinese entry guide or full-tree translation is required. Do not expand the model, reward or training pool while organizing it.

## 2. Prerequisites: reward, potions and required relic state

This prerequisite block comes before new initial-state dataset work. Retain the previously agreed reward/potion -> required relic sequence. Complete and validate the reward revision, required potion handling/use-cost behavior, and required relic state/mechanisms before advancing. I8 approves A-path `battle_reward_v2` with B=2, alpha=1 and lambda=0.05, paid once at true termination. The [implementation report](../reward-potion-v2-report.md) records current validation. The first relic implementation slice is recorded in the I9 progress section below; remaining relic work is still required before closing this prerequisite block. Preserve the current A-path backbone and source/conditional-target policy. The aim is faithful independent Act 1/2 combat, with required owned relic instances and public state represented, rather than silently dropping unsupported scene components.

Prepared material:

- [Relic audit/import plan v1](sts-relic-audit-and-import-plan-v1.md): exact copy of the owner's prepared 2026-09-14 document; source hash recorded in the migration manifest. Its baseline was refreshed against reward-v2 commit `1e95005` for the first I9 slice. Unimplemented batches remain pending; its identity-embedding suggestion is superseded by the owner's one-hot decision.
- [Existing static relic/potion audit](../relic-potion-backend-audit.md): implementation references, not per-relic behavior certification.
- [Act 1/2 integration evidence](../act12-main-integration-report.md): existing environment boundary, not proof of all combinations.
- [Current A-path integration](../a-path-main-integration-report.md) and [relation design](../stasis-relation-design-review.md): preserve accepted mechanisms and distinguish their evidence levels.

At the start of that work, agree on an exact scene/mechanism coverage matrix, initialization and public dynamic-state requirements, recovery behavior, and admission criteria. Inventory prior preparation before implementing replacements. Full original-game equivalence is not established by the current coverage counts. This cleanup does not start this stage.

## 3. Deferred A+B initial-state preparation

After section 2 is complete and validated, investigate `SlayTheData.7z` using the [initial-state source work item](initial-state-source-plan.md). The owner chose A (verified real-record reconstruction) plus B (explicitly constructed scenes based on reliable source material). First establish what fields and scenes can actually be recovered; current metadata is not proof of a usable large training corpus. Do not start this investigation alongside the prerequisite work.

Candidate preparation does not authorize admission. Obtain owner verification for new scope/distribution decisions; then validate and freeze the environment, reward, pool, evaluation protocol and explicit budget before training. Further mechanism gaps discovered during this stage return to the owner rather than silently changing scope.

## 4. Evidence, training evaluation and reproduction

Recover the original configuration/source/backend of the located A-path run. Verify checkpoints and raw evaluation records, then determine which result is reproducible and what remains missing. Keep its historical identity separate from the current main fingerprint. Establish an accessible clean-clone evaluation/report route before claiming public reproducibility. New experiments require a frozen protocol and a new explicit budget; do not train merely to obtain a favorable comparison.

Historical evidence may support the later comparison, but it cannot be relabeled under the revised reward. The new source-preparation stage must remain after the prerequisite block unless the owner explicitly changes that ordering.

## Later

Decision Transformer, broader generalization studies and any focused ablation remain later research. MLP stays frozen to the earlier comparison; no expansion or additional MLP study is required here.

## External refactor proposal

The 2026-09-15 downloaded research-refactor plan and reading guide informed discussion, but their embedded M0–M6 prompts are not the adopted execution scope. The owner-approved scope is I6. In particular, full English migration, new training and clean-clone reproduction are not first-pass completion gates. No second competing specification is introduced.

## I9 implementation progress

The first relic implementation slice is available in [the integration report](../relic-integration-report.md): one-hot identity, existing eight relics and six counter representatives. It is scoped diagnostic evidence, not full R0 completion or new pool admission. Special relics require owner review. The historical plan remains a planning input; I8 reward v2 and I9 one-hot identity supersede its corresponding older suggestions.

## I10 full audit and second batch

The [Act 1/2 scope audit](../act12-relic-audit.md) is complete as a static catalog/state-risk review, with 148 standard Ironclad candidates and explicit exclusions. The [second batch](../relic-second-batch-report.md) adds eight ordinary diagnostic imports, bringing the registry to 22; its 25-dimensional one-hot-plus-state input retains the 64-dimensional backbone. Special review and later batches remain pending. No new training admission or dataset preparation is authorized by these results.
