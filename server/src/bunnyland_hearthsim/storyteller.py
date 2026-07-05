"""Communal-feast storyteller incident (mechanic 10).

The pack registers one storyteller incident of its own: every so often the settlement
*hungers for a communal feast*. :class:`CommunalFeastConsequence` declares the incident in
the busiest occupied room, reusing the **core** storyteller entities and events
(:class:`~bunnyland.mechanics.storyteller.IncidentComponent`, ``IncidentStartedEvent``,
``IncidentResolvedEvent``) rather than inventing a parallel system. Cooking for the room —
sharing a meal or, best of all, catering the table — resolves it (see
:func:`resolve_feast_incident`), so the headline mechanic answers the world pressure.

Scheduling is a pure function of the world epoch and a :class:`FeastStorytellerComponent`
config marker, so incidents are paced deterministically.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    container_of,
    spawn_entity,
)
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.mechanics.storyteller import (
    SECONDS_PER_DAY,
    IncidentComponent,
    IncidentResolvedEvent,
    IncidentStartedEvent,
)
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

#: The incident kind this pack contributes to the storyteller.
INCIDENT_KIND = "communal_feast"


@dataclass(frozen=True)
class FeastStorytellerComponent(Component):
    """Config marker pacing communal-feast incidents (a world singleton)."""

    enabled: bool = True
    interval_seconds: int = SECONDS_PER_DAY
    next_epoch: int = SECONDS_PER_DAY


class CommunalFeastCalledEvent(DomainEvent):
    """The settlement is hungry for a communal feast in a room."""

    incident_id: str
    feast_room_id: str


def spawn_feast_storyteller(
    world: World, *, interval_seconds: int = SECONDS_PER_DAY, next_epoch: int | None = None
) -> Entity:
    """Spawn the communal-feast config marker (idempotent: returns any existing one)."""
    existing = next(
        iter(world.query().with_all([FeastStorytellerComponent]).execute_entities()), None
    )
    if existing is not None:
        return existing
    return spawn_entity(
        world,
        [
            IdentityComponent(name="communal feast storyteller", kind="config"),
            FeastStorytellerComponent(
                interval_seconds=interval_seconds,
                next_epoch=interval_seconds if next_epoch is None else next_epoch,
            ),
        ],
    )


def _occupied_rooms(world: World) -> dict[object, int]:
    """Room id -> number of live characters standing in it."""
    counts: dict[object, int] = {}
    for character in world.query().with_all([CharacterComponent]).execute_entities():
        room_id = container_of(character)
        if room_id is not None and world.has_entity(room_id):
            room = world.get_entity(room_id)
            if room.has_component(RoomComponent):
                counts[room_id] = counts.get(room_id, 0) + 1
    return counts


def _busiest_room(world: World) -> Entity | None:
    """The most-occupied room (ties broken by id for determinism), or ``None``."""
    counts = _occupied_rooms(world)
    if not counts:
        return None
    best_id = min(counts, key=lambda room_id: (-counts[room_id], str(room_id)))
    return world.get_entity(best_id)


def pending_feast_incident(world: World, room: Entity) -> Entity | None:
    """The unresolved communal-feast incident sitting in ``room``, or ``None``."""
    for _edge, target_id in room.get_relationships(Contains):
        if not world.has_entity(target_id):
            continue
        entity = world.get_entity(target_id)
        if not entity.has_component(IncidentComponent):
            continue
        incident = entity.get_component(IncidentComponent)
        if incident.kind == INCIDENT_KIND and incident.resolved_at_epoch is None:
            return entity
    return None


def _declare_incident(world: World, room: Entity, epoch: int) -> Entity:
    incident = spawn_entity(
        world,
        [
            IdentityComponent(name="communal feast", kind="incident"),
            IncidentComponent(
                kind=INCIDENT_KIND,
                budget_spent=0.0,
                started_at_epoch=epoch,
                room_id=str(room.id),
            ),
        ],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), incident.id)
    return incident


def resolve_feast_incident(
    world: World, room: Entity | None, epoch: int, *, actor_id: str
) -> IncidentResolvedEvent | None:
    """Resolve a pending communal-feast incident in ``room`` (a shared meal answered it)."""
    if room is None:
        return None
    incident_entity = pending_feast_incident(world, room)
    if incident_entity is None:
        return None
    incident = incident_entity.get_component(IncidentComponent)
    replace_component(incident_entity, replace(incident, resolved_at_epoch=epoch))
    return IncidentResolvedEvent(
        **event_base(
            epoch,
            default_visibility=EventVisibility.ROOM,
            actor_id=actor_id,
            room_id=str(room.id),
            target_ids=(str(incident_entity.id),),
            incident_id=str(incident_entity.id),
            kind=INCIDENT_KIND,
        )
    )


class CommunalFeastConsequence:
    """Declare a communal-feast incident in the busiest room when one is due."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        query = world.query().with_all([FeastStorytellerComponent])
        for config_entity in query.execute_entities():
            config = config_entity.get_component(FeastStorytellerComponent)
            if not config.enabled or epoch < config.next_epoch:
                continue
            room = _busiest_room(world)
            if room is None:
                continue
            replace_component(
                config_entity,
                replace(config, next_epoch=epoch + config.interval_seconds),
            )
            if pending_feast_incident(world, room) is not None:
                continue
            incident = _declare_incident(world, room, epoch)
            events.append(
                IncidentStartedEvent(
                    **event_base(
                        epoch,
                        default_visibility=EventVisibility.ROOM,
                        actor_id=str(config_entity.id),
                        room_id=str(room.id),
                        target_ids=(str(incident.id),),
                        incident_id=str(incident.id),
                        kind=INCIDENT_KIND,
                        room_id_started=str(room.id),
                    )
                )
            )
            events.append(
                CommunalFeastCalledEvent(
                    **event_base(
                        epoch,
                        default_visibility=EventVisibility.ROOM,
                        actor_id=str(config_entity.id),
                        room_id=str(room.id),
                        target_ids=(str(incident.id),),
                        incident_id=str(incident.id),
                        feast_room_id=str(room.id),
                    )
                )
            )
        return events


def install_storyteller(actor) -> None:
    """Register the communal-feast consequence and seed its pacing marker.

    A ``service_factories`` entry (mirrors wildsim's ``install_predators``): it wires the
    per-tick :class:`CommunalFeastConsequence` and idempotently spawns the world's single
    :class:`FeastStorytellerComponent` config marker.
    """
    actor.register_consequence(CommunalFeastConsequence())
    spawn_feast_storyteller(actor.world)


def feast_storyteller_fragments(world: World, character: Entity) -> list[str]:
    """Prompt line when the character's room is awaiting a communal feast."""
    room_id = container_of(character)
    if room_id is None or not world.has_entity(room_id):
        return []
    room = world.get_entity(room_id)
    if pending_feast_incident(world, room) is None:
        return []
    return ["The settlement is hungry for a communal feast here."]


__all__ = [
    "INCIDENT_KIND",
    "CommunalFeastCalledEvent",
    "CommunalFeastConsequence",
    "FeastStorytellerComponent",
    "feast_storyteller_fragments",
    "install_storyteller",
    "pending_feast_incident",
    "resolve_feast_incident",
    "spawn_feast_storyteller",
]
