"""Behaviour tests for the v2 communal-feast storyteller incident (mechanic 10)."""

from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.mechanics.storyteller import IncidentComponent, IncidentStartedEvent

from bunnyland_hearthsim.storyteller import (
    INCIDENT_KIND,
    CommunalFeastCalledEvent,
    CommunalFeastConsequence,
    FeastStorytellerComponent,
    feast_storyteller_fragments,
    install_storyteller,
    pending_feast_incident,
    resolve_feast_incident,
    spawn_feast_storyteller,
)


def _room(actor, title="Hall"):
    return spawn_entity(actor.world, [RoomComponent(title=title)])


def _character(actor, room, name="Vil"):
    character = spawn_entity(
        actor.world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def test_spawn_feast_storyteller_is_idempotent():
    actor = WorldActor()
    first = spawn_feast_storyteller(actor.world, interval_seconds=100, next_epoch=50)
    assert first.get_component(FeastStorytellerComponent).next_epoch == 50
    again = spawn_feast_storyteller(actor.world)
    assert again.id == first.id  # only ever one marker
    markers = list(actor.world.query().with_all([FeastStorytellerComponent]).execute_entities())
    assert len(markers) == 1


def test_consequence_declares_feast_in_the_busiest_room():
    actor = WorldActor()
    quiet = _room(actor, "Quiet")
    busy = _room(actor, "Busy")
    _character(actor, quiet, "Solo")
    _character(actor, busy, "A")
    _character(actor, busy, "B")
    spawn_feast_storyteller(actor.world, interval_seconds=100, next_epoch=0)

    events = CommunalFeastConsequence().process(actor.world, 0)

    assert any(isinstance(e, IncidentStartedEvent) for e in events)
    called = next(e for e in events if isinstance(e, CommunalFeastCalledEvent))
    assert called.feast_room_id == str(busy.id)  # the crowd draws the feast
    pending = pending_feast_incident(actor.world, busy)
    assert pending is not None
    assert pending.get_component(IncidentComponent).kind == INCIDENT_KIND


def test_consequence_waits_its_turn_and_skips_duplicates():
    actor = WorldActor()
    room = _room(actor)
    _character(actor, room)
    spawn_feast_storyteller(actor.world, interval_seconds=100, next_epoch=100)

    # Before it is due: nothing happens.
    assert CommunalFeastConsequence().process(actor.world, 0) == []
    # Due: declares one feast.
    first = CommunalFeastConsequence().process(actor.world, 100)
    assert any(isinstance(e, CommunalFeastCalledEvent) for e in first)
    # Due again but the earlier feast is still unanswered: no duplicate incident.
    again = CommunalFeastConsequence().process(actor.world, 200)
    assert not any(isinstance(e, CommunalFeastCalledEvent) for e in again)
    incidents = list(actor.world.query().with_all([IncidentComponent]).execute_entities())
    assert len(incidents) == 1


def test_consequence_no_op_when_disabled_or_no_rooms():
    actor = WorldActor()
    spawn_feast_storyteller(actor.world, next_epoch=0)  # due, but no occupied rooms
    assert CommunalFeastConsequence().process(actor.world, 0) == []

    disabled = WorldActor()
    room = _room(disabled)
    _character(disabled, room)
    marker = spawn_feast_storyteller(disabled.world, next_epoch=0)
    from dataclasses import replace

    from bunnyland.core.ecs import replace_component

    replace_component(
        marker, replace(marker.get_component(FeastStorytellerComponent), enabled=False)
    )
    assert CommunalFeastConsequence().process(disabled.world, 0) == []


def test_resolve_feast_incident_handles_the_empty_cases():
    actor = WorldActor()
    room = _room(actor)
    # No room -> None.
    assert resolve_feast_incident(actor.world, None, 0, actor_id="x") is None
    # No pending incident -> None.
    assert resolve_feast_incident(actor.world, room, 0, actor_id="x") is None


def test_feast_fragment_appears_only_when_a_feast_is_pending():
    actor = WorldActor()
    room = _room(actor)
    diner = _character(actor, room)
    assert feast_storyteller_fragments(actor.world, diner) == []
    # Loose character with no room -> still empty.
    loose = spawn_entity(
        actor.world, [IdentityComponent(name="Wanderer", kind="character"), CharacterComponent()]
    )
    assert feast_storyteller_fragments(actor.world, loose) == []

    spawn_feast_storyteller(actor.world, next_epoch=0)
    CommunalFeastConsequence().process(actor.world, 0)
    assert feast_storyteller_fragments(actor.world, diner) == [
        "The settlement is hungry for a communal feast here."
    ]


def test_install_storyteller_registers_and_seeds():
    actor = WorldActor()
    install_storyteller(actor)
    markers = list(actor.world.query().with_all([FeastStorytellerComponent]).execute_entities())
    assert len(markers) == 1
