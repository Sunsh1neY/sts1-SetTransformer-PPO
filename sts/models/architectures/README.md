# Architecture variants

- `m0_baseline/`: frozen M0 entry point, aliasing `sts.models.apath.APathActorCritic`.
  The implementation stays at its fingerprinted historical path. No duplicate source
  or checkpoint conversion is introduced.
- `m2a_source_context/`: independent one-seed source-context PMA and residual
  dynamic task query. Existing END_TURN PMA/head, target pointer and critic topology
  remain unchanged.

Use `from sts.models.architectures import build_model`, then
`build_model("m2a_source_context")`. Unknown names fail closed.
Python package names use snake_case; architecture versions differ.

## Exact M2a design

Width 64, four heads, FF128; shared/actor/critic SAB counts stay 2/2/2.
The new PMA reads actor entity tokens, with the entity-valid mask.
For each task, concatenate its learned query and the 64-D context, then apply
Linear(128,64), GELU, Linear(64,64), and add this delta to the learned query.
The final delta layer is zero-initialized: paired fresh random seeds reproduce
M0 outputs initially. The context pool and first delta layer receive zero gradient
on the first backward pass; they become trainable through the nonzero output layer
after updates. This is an explicit initialization choice, not trained-weight reuse.

All source-context PMA parameters are separate from END_TURN pooling.
Source-only raw-score gradients do not reach END_TURN pooling; the shared actor
encoder still couples representation learning, and the joint softmax still couples
END_TURN probability to other source scores. This is intentional.

No M1, multi-query, target redesign, trainer integration, checkpoint registry
admission, corpus/reward change, or training launch is included.
Existing training and console entry points still select M0. New model checkpoints
must retain their distinct model_version and be loaded strictly; never load M0
weights with strict=False as an implicit architecture migration.
