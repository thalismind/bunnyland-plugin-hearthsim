"""Coverage for spatial helpers, the appliance-recipe lookup, and cook skill/stove branches."""

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

from bunnyland_hearthsim import holder_of, room_of, spawn_ingredient, spawn_stove
from bunnyland_hearthsim.cooking import CookHandler
from bunnyland_hearthsim.recipes import appliance_recipe_by_name
from bunnyland_hearthsim.skill import CookingSkillComponent, CookingSkillImprovedEvent


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


def test_appliance_recipe_by_name_lookup():
    assert appliance_recipe_by_name("grilled skewers").category == "grilled"
    assert appliance_recipe_by_name("moon pie") is None


def test_cook_at_a_named_stove_and_level_up():
    actor, room, cook = _kitchen()
    stove = spawn_stove(actor.world, room_id=room.id)
    from bunnyland.core.ecs import replace_component

    replace_component(cook, CookingSkillComponent(experience=8.0, meals_cooked=3))
    spawn_ingredient(actor.world, name="lettuce", tags=("vegetable",), holder=cook)
    spawn_ingredient(actor.world, name="tomato", tags=("vegetable",), holder=cook)

    result = CookHandler().execute(
        HandlerContext(world=actor.world, epoch=0),
        _cmd(cook.id, {"stove_id": str(stove.id), "recipe": "garden salad"}),
    )

    assert result.ok
    assert any(isinstance(e, CookingSkillImprovedEvent) for e in result.events)


def test_holder_of_resolves_carriers_only():
    actor, room, cook = _kitchen()
    carried = spawn_ingredient(actor.world, name="apple", tags=("fruit",), holder=cook)
    loose = spawn_ingredient(actor.world, name="pear", tags=("fruit",), room_id=room.id)
    orphan = spawn_entity(actor.world, [IdentityComponent(name="orphan", kind="item")])

    assert holder_of(actor.world, carried.id).id == cook.id
    assert holder_of(actor.world, loose.id) is None  # sitting in a room, not held
    assert holder_of(actor.world, orphan.id) is None  # uncontained
    assert holder_of(actor.world, "nope") is None  # missing entity


def test_room_of_walks_up_to_the_room():
    actor, room, cook = _kitchen()
    carried = spawn_ingredient(actor.world, name="apple", tags=("fruit",), holder=cook)
    loose = spawn_ingredient(actor.world, name="pear", tags=("fruit",), room_id=room.id)
    orphan = spawn_entity(actor.world, [IdentityComponent(name="orphan", kind="item")])

    assert room_of(actor.world, carried.id).id == room.id  # through the carrier
    assert room_of(actor.world, loose.id).id == room.id  # directly on the floor
    assert room_of(actor.world, orphan.id) is None  # nowhere
    assert room_of(actor.world, "nope") is None  # missing entity
