"""Explicit architecture selection; legacy training defaults remain unchanged."""

def build_model(name="m0_baseline"):
    if name == "m0_baseline":
        from .m0_baseline.model import M0ActorCritic
        return M0ActorCritic()
    if name == "m2a_source_context":
        from .m2a_source_context.model import M2aActorCritic
        return M2aActorCritic()
    raise ValueError(f"Unknown architecture: {name}")
