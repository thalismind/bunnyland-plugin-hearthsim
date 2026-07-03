from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.ecs import replace_component

from bunnyland_hearthsim import (
    BuffComponent,
    FreshnessComponent,
    hearthsim_fragments,
    spawn_meal,
    spawn_stove,
)
from bunnyland_hearthsim.recipes import recipe_by_name


def _scene():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Kitchen")])
    character = spawn_entity(
        actor.world, [IdentityComponent(name="Auguste", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return actor, room, character


def test_reachable_stove_is_described():
    actor, room, character = _scene()
    spawn_stove(actor.world, room_id=room.id)

    lines = hearthsim_fragments(actor.world, character)

    assert "Stove stands here, ready for cooking." in lines


def test_fresh_meal_reads_appetizing():
    actor, room, character = _scene()
    spawn_meal(actor.world, recipe_by_name("garden salad"), epoch=0, room_id=room.id)

    lines = hearthsim_fragments(actor.world, character)

    assert "Garden salad here looks fresh and appetizing." in lines


def test_spoiled_meal_reads_foul():
    actor, room, character = _scene()
    meal = spawn_meal(actor.world, recipe_by_name("garden salad"), epoch=0, room_id=room.id)
    replace_component(meal, replace(meal.get_component(FreshnessComponent), spoiled=True))

    lines = hearthsim_fragments(actor.world, character)

    assert "Garden salad here has spoiled and smells foul." in lines


def test_buff_is_shown_to_the_eater():
    actor, _room, character = _scene()
    replace_component(
        character, BuffComponent(name="hearty", started_at_epoch=0, expires_at_epoch=100)
    )

    lines = hearthsim_fragments(actor.world, character)

    assert "You feel hearty after a good meal." in lines


def test_no_lines_without_cooking_state():
    actor, _room, character = _scene()
    assert hearthsim_fragments(actor.world, character) == []
