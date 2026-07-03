"""Shared feasts (mechanic 5).

Eating a meal in a room with other characters is a *feast*: the diners share the moment,
warming their social bonds and easing loneliness. This reuses the core social layer —
``adjust_bond`` for the directed relationship edges and ``recover_daily_need`` for the
social meter — so a feast plugs straight into the same relationship state the rest of the
game reads.
"""

from __future__ import annotations

from bunnyland.core import CharacterComponent, container_of, contents
from bunnyland.core.events import DomainEvent
from bunnyland.mechanics.needs import SocialNeedComponent, recover_daily_need
from bunnyland.mechanics.social import adjust_bond
from relics import Entity, World

#: How much a shared meal warms each pairwise bond and relieves the social need.
FEAST_AFFINITY = 0.06
FEAST_FAMILIARITY = 0.04
FEAST_SOCIAL_RECOVERY = 10.0


class FeastEnjoyedEvent(DomainEvent):
    """A character shared a meal with others in the room."""

    eater_id: str
    diner_ids: tuple[str, ...]


def diners_in_room(world: World, eater: Entity) -> list[Entity]:
    """Return the other characters sharing ``eater``'s room, id-sorted for determinism."""
    room_id = container_of(eater)
    if room_id is None or not world.has_entity(room_id):
        return []
    others: list[Entity] = []
    for occupant_id in contents(world.get_entity(room_id)):
        if occupant_id == eater.id or not world.has_entity(occupant_id):
            continue
        occupant = world.get_entity(occupant_id)
        if occupant.has_component(CharacterComponent):
            others.append(occupant)
    return sorted(others, key=lambda entity: str(entity.id))


def share_feast(world: World, eater: Entity, epoch: int) -> list[Entity]:
    """Warm bonds and relieve the social need for everyone at a shared meal.

    Returns the co-diners (empty when the eater is alone, so no feast happened).
    """
    diners = diners_in_room(world, eater)
    if not diners:
        return []
    warmth = {"affinity": FEAST_AFFINITY, "familiarity": FEAST_FAMILIARITY}
    for diner in diners:
        adjust_bond(world, eater.id, diner.id, warmth)
        adjust_bond(world, diner.id, eater.id, warmth)
        if diner.has_component(SocialNeedComponent):
            recover_daily_need(
                diner,
                SocialNeedComponent,
                FEAST_SOCIAL_RECOVERY,
                epoch,
                timestamp_field="last_social_epoch",
            )
    if eater.has_component(SocialNeedComponent):
        recover_daily_need(
            eater,
            SocialNeedComponent,
            FEAST_SOCIAL_RECOVERY,
            epoch,
            timestamp_field="last_social_epoch",
        )
    return diners


__all__ = [
    "FEAST_AFFINITY",
    "FEAST_FAMILIARITY",
    "FEAST_SOCIAL_RECOVERY",
    "FeastEnjoyedEvent",
    "diners_in_room",
    "share_feast",
]
