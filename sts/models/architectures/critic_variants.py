"""Explicit independent variants; no mutation of historical model registry."""
from .m3a_multiseed import M3aActorCritic
from .c_w128 import CW128ActorCritic
from .c_d4 import CD4ActorCritic

MODELS = {"m3a": M3aActorCritic, "c_w128": CW128ActorCritic, "c_d4": CD4ActorCritic}
