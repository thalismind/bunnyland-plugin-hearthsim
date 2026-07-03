"""Spawn factories for the cooking pack.

The loader does not consume ``ContentContribution.prefabs``, so ingredients, stoves, and
cooked meals are created with these ``spawn_entity`` helpers (from the ``cook`` verb, tests,
admin tooling, or worldgen). Pass ``room_id`` to drop an item on a room's floor, ``holder``
to place it directly into a character's inventory, or neither to spawn it uncontained.
"""

from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    spawn_entity,
)
from bunnyland.mechanics.consumables import ConsumableComponent, FoodComponent
from relics import Entity, World

from .components import FreshnessComponent, IngredientComponent, MealComponent, StoveComponent
from .recipes import Recipe


def _link_into_room(world: World, item: Entity, room_id) -> None:
    if room_id is None or not world.has_entity(room_id):
        return
    world.get_entity(room_id).add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), item.id)


def _give_to_holder(item: Entity, holder: Entity | None) -> None:
    if holder is not None:
        holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def spawn_ingredient(
    world: World,
    *,
    name: str,
    tags: tuple[str, ...],
    room_id=None,
    holder: Entity | None = None,
) -> Entity:
    """Spawn a tagged ingredient item."""
    item = spawn_entity(
        world,
        [
            IdentityComponent(name=name, kind="item", tags=("hearthsim", "ingredient")),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            IngredientComponent(tags=tuple(tags)),
        ],
    )
    _link_into_room(world, item, room_id)
    _give_to_holder(item, holder)
    return item


def spawn_stove(world: World, *, room_id=None, name: str = "stove", heat: str = "gas") -> Entity:
    """Spawn a stove fixture, optionally placed in ``room_id``."""
    stove = spawn_entity(
        world,
        [
            IdentityComponent(name=name, kind="item", tags=("hearthsim", "stove")),
            StoveComponent(heat=heat),
        ],
    )
    _link_into_room(world, stove, room_id)
    return stove


def spawn_meal(
    world: World,
    recipe: Recipe,
    epoch: int,
    *,
    room_id=None,
    holder: Entity | None = None,
) -> Entity:
    """Spawn the cooked meal for ``recipe`` (fresh as of ``epoch``).

    A meal is also a core ``FoodComponent`` item, so it is recognised as food by the base
    eat path; the cooking pack's ``eat-meal`` verb additionally applies the meal's buff.
    """
    meal = spawn_entity(
        world,
        [
            IdentityComponent(name=recipe.name, kind="item", tags=("hearthsim", "meal")),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            ConsumableComponent(current_uses=1, max_uses=1),
            FoodComponent(nutrition=recipe.nutrition, satiety=recipe.satiety),
            MealComponent(
                name=recipe.name,
                buff=recipe.buff,
                buff_magnitude=recipe.buff_magnitude,
                buff_duration=recipe.buff_duration,
                satiety=recipe.satiety,
                nutrition=recipe.nutrition,
            ),
            FreshnessComponent(cooked_at_epoch=epoch, spoils_after=recipe.spoils_after),
        ],
    )
    _link_into_room(world, meal, room_id)
    _give_to_holder(meal, holder)
    return meal


__all__ = ["spawn_ingredient", "spawn_meal", "spawn_stove"]
