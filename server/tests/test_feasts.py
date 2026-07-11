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
from bunnyland.foundation.meters.mechanics import Meter
from bunnyland.foundation.needs.mechanics import HungerComponent, SocialNeedComponent
from bunnyland.foundation.social.mechanics import bond_between

from bunnyland_hearthsim import diners_in_room, share_feast, spawn_meal
from bunnyland_hearthsim.meals import EatMealHandler
from bunnyland_hearthsim.recipes import recipe_by_name


def _character(actor, room, name, *, social=None, hungry=None):
    components = [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    if social is not None:
        components.append(SocialNeedComponent(meter=Meter(value=social)))
    if hungry is not None:
        components.append(HungerComponent(meter=Meter(value=hungry)))
    entity = spawn_entity(actor.world, components)
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), entity.id)
    return entity


def test_no_diners_when_alone():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Nook")])
    eater = _character(actor, room, "Solo")
    assert diners_in_room(actor.world, eater) == []
    assert share_feast(actor.world, eater, epoch=0) == []


def test_shared_feast_warms_bonds_and_eases_loneliness():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Great Hall")])
    eater = _character(actor, room, "Host", social=80.0)
    guest = _character(actor, room, "Guest", social=80.0)

    diners = share_feast(actor.world, eater, epoch=100)

    assert [d.id for d in diners] == [guest.id]
    # Bonds warmed both directions.
    assert bond_between(actor.world, eater.id, guest.id).affinity > 0
    assert bond_between(actor.world, guest.id, eater.id).familiarity > 0
    # Social need relieved for both.
    assert eater.get_component(SocialNeedComponent).meter.value < 80.0
    assert guest.get_component(SocialNeedComponent).meter.value < 80.0


def test_eat_meal_emits_feast_event_with_company():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Table")])
    eater = _character(actor, room, "Diner", hungry=50.0)
    guest = _character(actor, room, "Friend")
    meal = spawn_meal(actor.world, recipe_by_name("garden salad"), epoch=0, holder=eater)

    command = build_submitted_command(
        character_id=str(eater.id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="eat-meal",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload={"meal_id": str(meal.id)},
    )
    result = EatMealHandler().execute(HandlerContext(world=actor.world, epoch=0), command)

    assert result.ok
    feast = next(e for e in result.events if type(e).__name__ == "FeastEnjoyedEvent")
    assert feast.diner_ids == (str(guest.id),)


def test_eat_meal_alone_emits_no_feast_event():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Table")])
    eater = _character(actor, room, "Diner", hungry=50.0)
    meal = spawn_meal(actor.world, recipe_by_name("garden salad"), epoch=0, holder=eater)

    command = build_submitted_command(
        character_id=str(eater.id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="eat-meal",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload={"meal_id": str(meal.id)},
    )
    result = EatMealHandler().execute(HandlerContext(world=actor.world, epoch=0), command)

    assert result.ok
    assert not any(type(e).__name__ == "FeastEnjoyedEvent" for e in result.events)
