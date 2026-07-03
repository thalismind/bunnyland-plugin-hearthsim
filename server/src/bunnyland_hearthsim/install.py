"""Runtime wiring: register the cooking pack's per-tick consequences."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .freshness import SpoilageConsequence
from .meals import BuffExpiryConsequence


def install_hearthsim(actor: WorldActor) -> None:
    """Register the spoilage and buff-expiry consequences (a ``service_factories`` entry)."""
    actor.register_consequence(SpoilageConsequence())
    actor.register_consequence(BuffExpiryConsequence())


__all__ = ["install_hearthsim"]
