# Deferred initial-state source preparation

Status: **deferred until prerequisite work is complete and validated**. Recorded 2026-09-18 under [decision I7](../decisions.md). Authority remains [spec-v6](../../spec-v6.md) with registered amendments. This is a work item, not an instruction to begin acquisition or expand the training pool.

## Start condition and order

First finish the previously agreed reward revision, potion handling/use-cost work, and required relic state/mechanism integration, with their acceptance checks. The previous reward/potion -> required relic ordering is retained. Do not start this dataset investigation in parallel merely because it is read-only.

Then proceed in this order:

1. Inspect a bounded sample from the identified source, if practical access permits; establish acquisition cost before a bulk download.
2. Audit reconstructible Act 1/2 battle-entry fields and classify A/B candidates and exclusions.
3. Propose the usable scene set, source-group split, sampling distribution and outstanding admission checks for owner verification.
4. Validate the accepted candidate scope and freeze environment, reward, pool and evaluation contracts, plus an explicit training budget.
5. Train and evaluate only under the resulting authorization. An action-head ablation is a later optional experiment.

## Source strategy selected by the owner

**A — real-record reconstruction.** Recover battle-entry state only when the source contains enough verified information. Record timing explicitly: a pre-combat state and a post-initialization snapshot are different interfaces. Source-derived cards, HP/max HP, relic identity and required counters, potions and other necessary fields must be supported by evidence. New environment randomness must not be described as exact replay of the original battle.

**B — declared constructed scenes.** Reuse reliable source material, such as a complete real deck, and separately declare chosen HP, encounter, relic/potion state and other configuration fields. Such choices define a new experiment scene; they do not recover missing historical facts. Missing source information must not be silently zero-filled or relabeled as observed.

Keep both provenance categories visible in the inventory and evaluation. Deduplicate content, isolate related source runs across splits, and inspect coverage rather than inflating unique-state counts with random seeds. The mixture weights and expanded training distribution have not been decided.

## Identified source and present evidence

The owner confirmed `SlayTheData.7z`, whose project locator is https://archive.org/details/slay-the-data.-7z. The [existing local audit](../m2-public-data-audit.md) records historical metadata of 29,074,129,887 bytes (about 29.1 GB decimal) and a publisher claim of more than 77 million runs. Those are historical metadata/description observations, not currently verified population statistics. The old audit did not download the complete archive or validate its members. Current accessibility, sampling options, schema, usable Ironclad/Act 1/2 population and data-use terms remain to be checked after the prerequisites.

The smaller [previous corpus audit](../m2-corpus-report.md) and [existing sampler](../../sts/env/apath.py) are reusable references. Historical exclusions tied to an old backend must be rechecked against the then-current implementation; old candidate counts are not current admission counts.

## Expected deliverable

Produce a short English source audit plus a machine-readable candidate/exclusion ledger recording:

- Actual acquisition/sample scope and hashes; sampling bias and unverified archive claims.
- Recoverable and missing battle-entry fields, especially dynamic relic state and potion history.
- Deduplicated source groups and scene counts, separating A, B and exclusions.
- Coverage of acts/encounters, decks, HP ranges, relics and potions; gaps relevant to the intended training task.
- Feasibility/cost of further extraction and the exact owner decisions needed before changing admission or sampling.

Enough means supporting an explicitly bounded experiment, not reaching an arbitrary file count. No usable sample count, full Act 1/2 coverage, exact replay or training readiness is promised in advance.

## If additional gaps appear

Save the concrete example and explain whether it needs missing data, a deliberately constructed B scene, or additional mechanism work. Return scope/admission choices to the owner. Do not silently remove unsupported relics, guess counters, broaden implementation or weaken checkpoint/version checks.

## Actions taken in this recording pass

Documentation only. No new dataset download/sample extraction, mechanism implementation, reward change, training-pool modification or training run was performed.
