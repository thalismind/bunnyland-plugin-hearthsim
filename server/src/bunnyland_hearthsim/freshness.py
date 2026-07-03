"""Food freshness and spoilage (mechanic 4).

Cooked food carries a :class:`~bunnyland_hearthsim.components.FreshnessComponent` recording
when it was made and how long it keeps. :class:`SpoilageConsequence` runs each tick and,
purely from the world epoch and the food's own timestamps (no randomness, no wall clock),
flips it to spoiled once it is past its keep time. A spoiled meal also marks its core
``FoodComponent`` spoiled so the rest of the game treats it as bad food, and the cooking
pack's ``eat-meal`` verb withholds the buff.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, event_base
from bunnyland.mechanics.consumables import FoodComponent
from relics import World

from .components import FreshnessComponent

FRESH = "fresh"
STALE = "stale"
SPOILED = "spoiled"

#: Fraction of shelf life after which food reads as "stale" (but is still edible).
STALE_FRACTION = 0.6


def freshness_state(component: FreshnessComponent, epoch: int) -> str:
    """Coarse freshness band for a food at ``epoch``: fresh < stale < spoiled."""
    if component.spoiled:
        return SPOILED
    age = epoch - component.cooked_at_epoch
    if age >= component.spoils_after:
        return SPOILED
    if age >= component.spoils_after * STALE_FRACTION:
        return STALE
    return FRESH


class FoodSpoiledEvent(DomainEvent):
    """A food item spoiled."""

    item_id: str


class SpoilageConsequence:
    """Flip food to spoiled once it outlives its freshness (mechanic 4)."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for entity in list(world.query().with_all([FreshnessComponent]).execute_entities()):
            freshness = entity.get_component(FreshnessComponent)
            if freshness.spoiled:
                continue
            if epoch - freshness.cooked_at_epoch >= freshness.spoils_after:
                replace_component(entity, replace(freshness, spoiled=True))
                if entity.has_component(FoodComponent):
                    replace_component(
                        entity, replace(entity.get_component(FoodComponent), spoiled=True)
                    )
                events.append(
                    FoodSpoiledEvent(
                        **event_base(
                            epoch,
                            target_ids=(str(entity.id),),
                            item_id=str(entity.id),
                        )
                    )
                )
        return events


__all__ = [
    "FRESH",
    "SPOILED",
    "STALE",
    "STALE_FRACTION",
    "FoodSpoiledEvent",
    "SpoilageConsequence",
    "freshness_state",
]
