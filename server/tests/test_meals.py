from __future__ import annotations

from dataclasses import replace

import pytest
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
from bunnyland.core.ecs import replace_component
from bunnyland.core.handlers import HandlerContext
from bunnyland.foundation.meters.mechanics import Meter
from bunnyland.foundation.needs.mechanics import HungerComponent
from conftest import execute_handler

from bunnyland_hearthsim import BuffComponent, FreshnessComponent, spawn_meal
from bunnyland_hearthsim.meals import BuffExpiryConsequence, EatMealHandler
from bunnyland_hearthsim.recipes import RECIPES, recipe_by_name


def _eater(actor, room, *, hungry=60.0):
    eater = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="Colette", kind="character"),
            CharacterComponent(),
            HungerComponent(meter=Meter(value=hungry)),
        ],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), eater.id)
    return eater


def _scenario(**kwargs):
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Dining Room")])
    eater = _eater(actor, room, **kwargs)
    return actor, room, eater


def _cmd(character_id, meal_id):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="eat-meal",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload={"meal_id": str(meal_id)},
    )


def _ctx(actor, epoch=0):
    return HandlerContext(world=actor.world, epoch=epoch)


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda recipe: recipe.name)
def test_every_recipe_grants_its_buff_when_eaten(recipe):
    # A fresh meal of each recipe applies that recipe's buff for its full duration.
    actor, _room, eater = _scenario(hungry=90.0)
    meal = spawn_meal(actor.world, recipe, epoch=0, holder=eater)

    result = execute_handler(EatMealHandler(), _ctx(actor), _cmd(eater.id, meal.id))

    assert result.ok
    buff = eater.get_component(BuffComponent)
    assert buff.name == recipe.buff
    assert buff.expires_at_epoch == recipe.buff_duration


def test_eating_a_meal_restores_hunger_and_applies_buff():
    actor, _room, eater = _scenario(hungry=60.0)
    meal = spawn_meal(actor.world, recipe_by_name("hearty stew"), epoch=0, holder=eater)

    result = execute_handler(EatMealHandler(), _ctx(actor), _cmd(eater.id, meal.id))

    assert result.ok
    # Hunger fell by the meal's satiety (45 for stew).
    assert eater.get_component(HungerComponent).meter.value == 15.0
    assert eater.has_component(BuffComponent)
    assert eater.get_component(BuffComponent).name == "hearty"
    # The meal was consumed.
    assert not actor.world.has_entity(meal.id)


def test_eating_emits_core_food_event():
    actor, _room, eater = _scenario()
    meal = spawn_meal(actor.world, recipe_by_name("garden salad"), epoch=0, holder=eater)

    result = execute_handler(EatMealHandler(), _ctx(actor), _cmd(eater.id, meal.id))

    kinds = {type(event).__name__ for event in result.events}
    assert "FoodEatenEvent" in kinds
    assert "HungerChangedEvent" in kinds
    assert "MealEatenEvent" in kinds


def test_spoiled_meal_gives_no_buff_and_less_satiety():
    actor, _room, eater = _scenario(hungry=60.0)
    meal = spawn_meal(actor.world, recipe_by_name("hearty stew"), epoch=0, holder=eater)
    freshness = meal.get_component(FreshnessComponent)
    replace_component(meal, replace(freshness, spoiled=True))

    result = execute_handler(EatMealHandler(), _ctx(actor), _cmd(eater.id, meal.id))

    assert result.ok
    assert not eater.has_component(BuffComponent)
    # Spoiled satiety is 45 * 0.4 = 18, so hunger falls only to 42.
    assert eater.get_component(HungerComponent).meter.value == 42.0
    assert any(
        type(event).__name__ == "MealEatenEvent" and event.spoiled for event in result.events
    )


def test_buff_expires_after_its_duration():
    actor, _room, eater = _scenario()
    meal = spawn_meal(actor.world, recipe_by_name("garden salad"), epoch=0, holder=eater)
    execute_handler(EatMealHandler(), _ctx(actor, epoch=0), _cmd(eater.id, meal.id))
    buff = eater.get_component(BuffComponent)
    assert buff.expires_at_epoch == 14400  # garden salad buff_duration, cooked at epoch 0

    consequence = BuffExpiryConsequence()
    # Before expiry: buff stays.
    consequence.process(actor.world, buff.expires_at_epoch - 1)
    assert eater.has_component(BuffComponent)
    # At expiry: buff removed and an event emitted.
    events = consequence.process(actor.world, buff.expires_at_epoch)
    assert not eater.has_component(BuffComponent)
    assert [type(event).__name__ for event in events] == ["BuffExpiredEvent"]


def test_eat_meal_rejects_non_meal_item():
    actor, _room, eater = _scenario()
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    eater.add_relationship(Contains(mode=ContainmentMode.INVENTORY), rock.id)

    result = execute_handler(EatMealHandler(), _ctx(actor), _cmd(eater.id, rock.id))

    assert not result.ok
    assert result.reason == "that is not a meal"


def test_eat_meal_rejects_unreachable_meal():
    actor, room, eater = _scenario()
    other_room = spawn_entity(actor.world, [RoomComponent(title="Cellar")])
    meal = spawn_meal(actor.world, recipe_by_name("garden salad"), epoch=0, room_id=other_room.id)

    result = execute_handler(EatMealHandler(), _ctx(actor), _cmd(eater.id, meal.id))

    assert not result.ok
    assert result.reason == "the meal is not within reach"


def test_eat_meal_rejects_character_without_hunger():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Hall")])
    eater = spawn_entity(
        actor.world, [IdentityComponent(name="Ghost", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), eater.id)
    meal = spawn_meal(actor.world, recipe_by_name("garden salad"), epoch=0, holder=eater)

    result = execute_handler(EatMealHandler(), _ctx(actor), _cmd(eater.id, meal.id))

    assert not result.ok
    assert result.reason == "character cannot eat"
