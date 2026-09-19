# Versioned diagnostic initial-state corpora

Corpus version and state schema version are separate: both A-v1 and A-v2 use `battle-initial-state-v2` canonical records. Neither is admitted to the formal training pool.

| Directory | Purpose | Content |
|---|---|---|
| `a-v1/` | Frozen initial baseline | 1,377 unchanged canonical states and original runtime/coverage evidence |
| `a-v2/` | Frozen coverage augmentation | 1,715 states: the unchanged baseline plus 338 configured variants |

## Files

- `a-v1/states.jsonl`: authoritative baseline consumer input. The old v1-labeled wrapper is retained separately as `legacy-admitted-a-corpus.jsonl`, without rewriting its historical bytes.
- `a-v1/manifest.json`: hashes of frozen baseline data and evidence. Copied scripts preserve historical evidence; run maintained scripts from the project root, not from the snapshot directory.
- `a-v2/states.jsonl`: complete baseline-plus-augmentation input.
- `a-v2/additions.jsonl`: augmentation only, for diagnostics and ablation bookkeeping.
- `a-v2/lineage.jsonl`: category, parent hash, changed fields, parameters and inherited split for every addition.
- `a-v2/generation-policy.json`: exact deterministic generation rules and deferred work.
- `a-v2/validation/`: new-state runtime evidence and before/after coverage checks.
- `a-v2/manifest.json`: dataset and validation fingerprints; diagnostic status, not training admission.

## A-v2 categories

1. **Act 2 low HP (138)**: one existing parent per connected component with Act 2 coverage; set HP to 10% or 25% of existing max HP, rounded down and bounded below by one.
2. **Entry counters (164)**: enumerate registered legal values of Pen Nib, Nunchaku, Happy Flower, Incense Burner, Ink Bottle and Sundial on existing owned instances. Select at most two parent components per identity and partition; unchanged states are deduplicated. Enumeration replaces random draws to guarantee reproducible phase coverage. Other stateful relics are not randomized.
3. **Rare combinations (36)**: append missing zero-upgrade cards for four explicit combinations to three existing Act 2 parent components per partition. Existing cards and relics remain. These are controlled synthetic combinations, not reconstructed historical decks or certified functional archetypes.

## Interpretation and use

Parent origins describe the real source backbone; `evidence.augmentation` describes synthetic changes. All variants inherit the parent's connected component and partition. Added states do not increase independent source count. They must not be shuffled across train/dev/holdout boundaries. Synthetic holdout support is not an unseen-combination SAB generalization experiment.

No sampling weights are specified. Sampling the entire A-v2 file uniformly would change source and category exposure; the corpus does not silently install that policy. Compare versions using the same declared evaluation population if measuring the effect of augmentation.

Burning elites and the future SAB generalization corpus remain deferred; no empty directory is created for the latter. Old project-root artifacts remain as historical workflow outputs and are not moved or deleted.

## Verification

Run from the worktree root:

```powershell
python -B projects/battle-initial-states/version-corpora.py verify
python -B projects/battle-initial-states/certify-corpora.py
```

The generator refuses to overwrite an existing A-v2 directory. A-v1 freeze is idempotent only when all existing fingerprints match. New changes should receive a new corpus version.
