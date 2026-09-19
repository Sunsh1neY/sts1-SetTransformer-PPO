# A-path split actor/critic architecture v5

Date: 2026-09-19. Implementation authorized by the owner. Training remains pending protocol approval.

## Search result

No matching 2+2+2 SAB implementation was found in the current model sources of the four registered STS worktrees, the visible all-branch Git history search for branch-specific SAB names, or the memory registry. This is a scoped search result, not a claim about inaccessible or deleted history. The inspected A-path implementation had four fully shared blocks.

## Implemented topology

```text
Type projections + type embeddings + relation fusion
                      |
                Shared SAB x2
                 /          \
         Actor SAB x2      Critic SAB x2
          Actor norm        Critic norm
          /       \             |
 Source/target   Actor PMA   Critic PMA
   pointers      End-turn   Value MLP 64->64->1
```

Each SAB uses width 64, four heads, FF128/GELU, pre-LayerNorm and residuals. Each PMA has one learned seed and independent parameters. Shared type projections, embeddings, relation fusion and shared SAB blocks receive both losses. Branch-specific blocks, normalization, pooling and heads receive only their branch's loss. The actor continues to use source-then-conditional-target actions with unchanged masks, joint log probability and exact joint entropy.

Parameter count: **370,562**, up from **269,954** (+100,608, approximately 37.27%). Model version: `a-path-shared2-actor2-critic2-pma-pointer-relic-v5`. Model state keys change and strict loading rejects the old topology; the trainer's existing source fingerprint also changes. Old checkpoint fingerprints are not relaxed.

## Verification

Command (existing backend build supplied through PYTHONPATH):

`python -B -m pytest tests/test_apath_split_trunk.py tests/test_apath.py -q`

Result: **24 passed**. Tests include private-branch perturbation isolation, actor/critic gradient separation with shared-trunk gradients, value-only consistency, state-dict round trip and legacy-key rejection, plus existing joint-probability, legal routing, entity permutation, padding and selection checks.

An existing gradient-coverage test initially referenced the removed `blocks.*` names; it now checks both shared blocks, all four private blocks and both pools. No behavior assertion was removed.

No training collector/PPO/checkpoint smoke or full A-v2 episode sweep was run for v5. Existing frozen corpus runtime reports remain byte-preserved evidence for their original model/code fingerprints. Do not refresh those fingerprints to make the old evidence appear current. The approved future smoke must exercise the new model and the new corpus adapter together.
