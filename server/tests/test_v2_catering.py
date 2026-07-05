"""Behaviour tests for the v2 headline catering mechanic (mechanic 9)."""

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
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.handlers import HandlerContext
from bunnyland.mechanics.meter import Meter
from bunnyland.mechanics.needs import HungerComponent, SocialNeedComponent
from bunnyland.mechanics.social import bond_between
from bunnyland.mechanics.storyteller import IncidentComponent, IncidentResolvedEvent

from bunnyland_hearthsim import spawn_ingredient, spawn_stove
from bunnyland_hearthsim.catering import (
    CateredFor,
    CaterHandler,
    MealCateredEvent,
    catering_bond,
    record_catering,
)
from bunnyland_hearthsim.skill import CookingSkillComponent, CookingSkillImprovedEvent


def _room(actor, title="Great Hall"):
    return spawn_entity(actor.world, [RoomComponent(title=title)])


def _place(room, entity):
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), entity.id)


def _caterer(actor, room, *, experience=0.0):
    caterer = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="Chef", kind="character"),
            CharacterComponent(),
            CookingSkillComponent(experience=experience, meals_cooked=3),
        ],
    )
    _place(room, caterer)
    return caterer


def _diner(actor, room, name, *, hungry=60.0, social=80.0, hunger=True):
    components = [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    if hunger:
        components.append(HungerComponent(meter=Meter(value=hungry)))
    if social is not None:
        components.append(SocialNeedComponent(meter=Meter(value=social)))
    diner = spawn_entity(actor.world, components)
    _place(room, diner)
    return diner


def _salad_ingredients(actor, caterer):
    spawn_ingredient(actor.world, name="lettuce", tags=("vegetable",), holder=caterer)
    spawn_ingredient(actor.world, name="tomato", tags=("vegetable",), holder=caterer)


def _cater(actor, caterer, epoch=0):
    command = build_submitted_command(
        character_id=str(caterer.id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="cater",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload={},
    )
    return CaterHandler().execute(HandlerContext(world=actor.world, epoch=epoch), command)


def test_cater_feeds_the_room_warms_bonds_and_levels_up():
    actor = WorldActor()
    room = _room(actor)
    caterer = _caterer(actor, room, experience=8.0)  # one salad crosses into home cook
    spawn_stove(actor.world, room_id=room.id)
    guest_a = _diner(actor, room, "Ada")
    guest_b = _diner(actor, room, "Ben")
    _salad_ingredients(actor, caterer)

    result = _cater(actor, caterer)

    assert result.ok
    catered = next(e for e in result.events if isinstance(e, MealCateredEvent))
    assert catered.recipe == "garden salad"
    assert set(catered.diner_ids) == {str(guest_a.id), str(guest_b.id)}
    # Bellies filled (hunger meter fell) for both diners.
    assert guest_a.get_component(HungerComponent).meter.value < 60.0
    assert guest_b.get_component(HungerComponent).meter.value < 60.0
    # Bonds warmed both directions and loneliness eased.
    assert bond_between(actor.world, caterer.id, guest_a.id).affinity > 0
    assert bond_between(actor.world, guest_a.id, caterer.id).trust > 0
    assert guest_a.get_component(SocialNeedComponent).meter.value < 80.0
    # A CateredFor edge records the feeding.
    edge = catering_bond(actor.world, caterer.id, guest_a.id)
    assert edge is not None and edge.times == 1 and edge.total_dishes == 1
    # Crossing a mastery tier emits the skill event.
    assert any(isinstance(e, CookingSkillImprovedEvent) for e in result.events)


def test_cater_resolves_a_pending_communal_feast_incident():
    actor = WorldActor()
    room = _room(actor)
    caterer = _caterer(actor, room)
    spawn_stove(actor.world, room_id=room.id)
    _diner(actor, room, "Guest")
    _salad_ingredients(actor, caterer)
    incident = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="communal feast", kind="incident"),
            IncidentComponent(
                kind="communal_feast", budget_spent=0.0, started_at_epoch=0, room_id=str(room.id)
            ),
        ],
    )
    _place(room, incident)

    result = _cater(actor, caterer, epoch=500)

    assert result.ok
    resolved = next(e for e in result.events if isinstance(e, IncidentResolvedEvent))
    assert resolved.incident_id == str(incident.id)
    assert incident.get_component(IncidentComponent).resolved_at_epoch == 500


def test_cater_capacity_caps_the_table_and_skips_the_hungerless():
    actor = WorldActor()
    room = _room(actor)
    caterer = _caterer(actor, room)  # novice -> seats 2
    spawn_stove(actor.world, room_id=room.id)
    # Three diners present; only two fit at a novice's table.
    _diner(actor, room, "A")
    _diner(actor, room, "B")
    _diner(actor, room, "C", hunger=False)  # no belly to fill, still counts toward capacity
    _salad_ingredients(actor, caterer)

    result = _cater(actor, caterer)

    assert result.ok
    catered = next(e for e in result.events if isinstance(e, MealCateredEvent))
    assert len(catered.diner_ids) == 2  # capped at capacity


def test_cater_serves_a_guest_lacking_hunger_and_social_needs():
    actor = WorldActor()
    room = _room(actor)
    caterer = _caterer(actor, room)
    spawn_stove(actor.world, room_id=room.id)
    # A guest with neither a belly nor a loneliness meter still gets a bond, never an error.
    guest = _diner(actor, room, "Ghost", hunger=False, social=None)
    _salad_ingredients(actor, caterer)

    result = _cater(actor, caterer)

    assert result.ok
    catered = next(e for e in result.events if isinstance(e, MealCateredEvent))
    assert catered.diner_ids == (str(guest.id),)
    assert bond_between(actor.world, caterer.id, guest.id).affinity > 0


def test_record_catering_strengthens_the_edge():
    actor = WorldActor()
    room = _room(actor)
    caterer = _caterer(actor, room)
    diner = _diner(actor, room, "Repeat")
    assert catering_bond(actor.world, caterer.id, diner.id) is None
    first = record_catering(actor.world, caterer.id, diner.id, dishes=1, epoch=10)
    assert isinstance(first, CateredFor) and first.times == 1
    second = record_catering(actor.world, caterer.id, diner.id, dishes=2, epoch=20)
    assert second.times == 2 and second.total_dishes == 3 and second.last_epoch == 20


def test_cater_rejections():
    actor = WorldActor()
    room = _room(actor)

    # invalid character id
    stray = _caterer(actor, room)
    bad = CaterHandler().execute(
        HandlerContext(world=actor.world, epoch=0),
        build_submitted_command(
            character_id="???",
            controller_id="ctrl",
            controller_generation=0,
            command_type="cater",
            cost=CommandCost(action=1),
            lane=Lane.WORLD,
            payload={},
        ),
    )
    assert bad.reason == "invalid character id"

    # no stove within reach
    assert _cater(actor, stray).reason == "no stove is within reach"

    # stove present but no ingredients
    spawn_stove(actor.world, room_id=room.id)
    assert _cater(actor, stray).reason == "you have no ingredients to cater with"

    # ingredients but nobody to cater for
    _salad_ingredients(actor, stray)
    assert _cater(actor, stray).reason == "no one here to cater for"


def test_cater_rejects_when_no_recipe_matches():
    actor = WorldActor()
    room = _room(actor)
    caterer = _caterer(actor, room)
    spawn_stove(actor.world, room_id=room.id)
    _diner(actor, room, "Guest")
    spawn_ingredient(actor.world, name="odd herb", tags=("herb",), holder=caterer)

    assert _cater(actor, caterer).reason == "no recipe matches your ingredients"
