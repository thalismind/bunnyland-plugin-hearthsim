"""Behaviour tests for the v2 appliance mechanic (mechanic 8)."""

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

from bunnyland_hearthsim import MealComponent, spawn_ingredient, spawn_stove
from bunnyland_hearthsim.appliances import (
    ApplianceComponent,
    appliance_categories,
    appliance_fragments,
    spawn_appliance,
    unlocked_appliance_recipes,
    unlocked_categories,
)
from bunnyland_hearthsim.cooking import CookHandler


def _kitchen():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Kitchen")])
    cook = spawn_entity(
        actor.world, [IdentityComponent(name="Remy", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), cook.id)
    return actor, room, cook


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="cook",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _cook(actor, cook, payload):
    return CookHandler().execute(HandlerContext(world=actor.world, epoch=0), _cmd(cook.id, payload))


def test_appliance_categories_lookup():
    assert appliance_categories("grill") == ("grilled",)
    assert appliance_categories("toaster") == ()  # unknown kind unlocks nothing


def test_unlocked_categories_and_recipes_follow_reachable_appliances():
    actor, room, cook = _kitchen()
    assert unlocked_categories(actor.world, cook) == frozenset()
    spawn_appliance(actor.world, kind="grill", room_id=room.id)
    categories = unlocked_categories(actor.world, cook)
    assert categories == frozenset({"grilled"})
    names = {recipe.name for recipe in unlocked_appliance_recipes(categories)}
    assert names == {"charred peppers", "grilled skewers"}


def test_spawn_appliance_is_a_stove_in_its_room():
    actor, room, _cook = _kitchen()
    grill = spawn_appliance(actor.world, kind="grill", room_id=room.id)
    from bunnyland_hearthsim.components import StoveComponent  # local: proves it doubles as a stove

    assert grill.has_component(StoveComponent)
    assert grill.get_component(ApplianceComponent).categories == ("grilled",)
    # Unplaced appliance simply stays uncontained.
    loose = spawn_appliance(actor.world, kind="oven")
    assert loose.has_component(ApplianceComponent)


def test_appliance_unlocks_its_category_recipe():
    actor, room, cook = _kitchen()
    spawn_appliance(actor.world, kind="grill", room_id=room.id)
    spawn_ingredient(actor.world, name="steak", tags=("meat",), holder=cook)
    spawn_ingredient(actor.world, name="pepper", tags=("vegetable",), holder=cook)
    spawn_ingredient(actor.world, name="thyme", tags=("herb",), holder=cook)

    result = _cook(actor, cook, {"recipe": "grilled skewers"})

    assert result.ok
    meals = list(actor.world.query().with_all([MealComponent]).execute_entities())
    assert meals[0].get_component(MealComponent).name == "grilled skewers"


def test_appliance_locked_recipe_is_rejected_on_a_plain_stove():
    actor, room, cook = _kitchen()
    spawn_stove(actor.world, room_id=room.id)  # a plain stove, no grill
    spawn_ingredient(actor.world, name="steak", tags=("meat",), holder=cook)
    spawn_ingredient(actor.world, name="pepper", tags=("vegetable",), holder=cook)
    spawn_ingredient(actor.world, name="thyme", tags=("herb",), holder=cook)

    result = _cook(actor, cook, {"recipe": "grilled skewers"})

    assert not result.ok
    assert result.reason == "you need a grill to cook grilled skewers"


def test_appliance_fragments_list_dishes_or_readiness():
    actor, room, cook = _kitchen()
    assert appliance_fragments(actor.world, cook) == []
    spawn_appliance(actor.world, kind="grill", room_id=room.id)
    spawn_appliance(actor.world, kind="toaster", room_id=room.id)  # unknown -> no dishes
    lines = appliance_fragments(actor.world, cook)
    assert "A grill here can cook charred peppers, grilled skewers." in lines
    assert "A toaster here is ready for cooking." in lines
