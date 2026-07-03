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
from bunnyland_hearthsim.cooking import CookHandler


def _scenario(*, with_stove=True):
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Kitchen")])
    cook = spawn_entity(
        actor.world, [IdentityComponent(name="Remy", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), cook.id)
    stove = spawn_stove(actor.world, room_id=room.id) if with_stove else None
    return actor, room, cook, stove


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


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


def _ctx(actor, epoch=0):
    return HandlerContext(world=actor.world, epoch=epoch)


def _meals_in(world):
    return list(world.query().with_all([MealComponent]).execute_entities())


def test_cook_produces_a_meal_and_consumes_ingredients():
    actor, _room, cook, _stove = _scenario()
    carrot = spawn_ingredient(actor.world, name="carrot", tags=("vegetable",), holder=cook)
    potato = spawn_ingredient(actor.world, name="potato", tags=("vegetable",), holder=cook)

    result = CookHandler().execute(_ctx(actor), _cmd(cook.id, {}))

    assert result.ok
    meals = _meals_in(actor.world)
    assert len(meals) == 1
    assert meals[0].get_component(MealComponent).name == "garden salad"
    # Ingredients consumed.
    assert not actor.world.has_entity(carrot.id)
    assert not actor.world.has_entity(potato.id)
    event = result.events[0]
    assert event.recipe == "garden salad"
    assert event.meal_id == str(meals[0].id)


def test_cook_rejects_when_no_stove_reachable():
    actor, _room, cook, _stove = _scenario(with_stove=False)
    spawn_ingredient(actor.world, name="carrot", tags=("vegetable",), holder=cook)
    spawn_ingredient(actor.world, name="potato", tags=("vegetable",), holder=cook)

    result = CookHandler().execute(_ctx(actor), _cmd(cook.id, {}))

    assert not result.ok
    assert result.reason == "no stove is within reach"


def test_cook_rejects_without_ingredients():
    actor, _room, cook, _stove = _scenario()

    result = CookHandler().execute(_ctx(actor), _cmd(cook.id, {}))

    assert not result.ok
    assert result.reason == "you have no ingredients to cook with"


def test_cook_rejects_when_no_recipe_matches():
    actor, _room, cook, _stove = _scenario()
    spawn_ingredient(actor.world, name="odd herb", tags=("herb",), holder=cook)

    result = CookHandler().execute(_ctx(actor), _cmd(cook.id, {}))

    assert not result.ok
    assert result.reason == "no recipe matches your ingredients"


def test_cook_rejects_unknown_named_recipe():
    actor, _room, cook, _stove = _scenario()
    spawn_ingredient(actor.world, name="carrot", tags=("vegetable",), holder=cook)
    spawn_ingredient(actor.world, name="potato", tags=("vegetable",), holder=cook)

    result = CookHandler().execute(_ctx(actor), _cmd(cook.id, {"recipe": "moon cheese"}))

    assert not result.ok
    assert result.reason == "unknown recipe"


def test_cook_rejects_missing_ingredients_for_named_recipe():
    actor, _room, cook, _stove = _scenario()
    spawn_ingredient(actor.world, name="carrot", tags=("vegetable",), holder=cook)

    result = CookHandler().execute(_ctx(actor), _cmd(cook.id, {"recipe": "hearty stew"}))

    assert not result.ok
    assert result.reason == "you are missing ingredients for hearty stew"


def test_cook_honours_a_named_recipe():
    actor, _room, cook, _stove = _scenario()
    spawn_ingredient(actor.world, name="carrot", tags=("vegetable",), holder=cook)
    spawn_ingredient(actor.world, name="beef", tags=("meat",), holder=cook)
    spawn_ingredient(actor.world, name="stock", tags=("broth",), holder=cook)

    result = CookHandler().execute(_ctx(actor), _cmd(cook.id, {"recipe": "hearty stew"}))

    assert result.ok
    assert _meals_in(actor.world)[0].get_component(MealComponent).name == "hearty stew"


def test_cook_rejects_invalid_character_id():
    actor, _room, _cook, _stove = _scenario()
    result = CookHandler().execute(_ctx(actor), _cmd("???", {}))
    assert not result.ok
    assert result.reason == "invalid character id"


def test_cook_rejects_non_stove_stove_id():
    actor, room, cook, _stove = _scenario()
    spawn_ingredient(actor.world, name="carrot", tags=("vegetable",), holder=cook)
    spawn_ingredient(actor.world, name="potato", tags=("vegetable",), holder=cook)
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), rock.id)

    result = CookHandler().execute(_ctx(actor), _cmd(cook.id, {"stove_id": str(rock.id)}))

    assert not result.ok
    assert result.reason == "that is not a stove"


def test_cook_rejects_unreachable_stove_id():
    actor, _room, cook, _stove = _scenario(with_stove=False)
    spawn_ingredient(actor.world, name="carrot", tags=("vegetable",), holder=cook)
    spawn_ingredient(actor.world, name="potato", tags=("vegetable",), holder=cook)
    far_room = spawn_entity(actor.world, [RoomComponent(title="Pantry")])
    far_stove = spawn_stove(actor.world, room_id=far_room.id)

    result = CookHandler().execute(_ctx(actor), _cmd(cook.id, {"stove_id": str(far_stove.id)}))

    assert not result.ok
    assert result.reason == "the stove is not within reach"
