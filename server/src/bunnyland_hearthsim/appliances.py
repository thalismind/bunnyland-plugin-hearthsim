"""Appliances that gate recipe categories (mechanic 8).

A plain :class:`~bunnyland_hearthsim.components.StoveComponent` cooks the whole base
cookbook and nothing more. An *appliance* — a grill, a smoker, an oven — is a stove that
*also* unlocks a category of appliance recipes (see
:data:`~bunnyland_hearthsim.recipes.APPLIANCE_RECIPES`). An appliance therefore carries both
a ``StoveComponent`` (so the ordinary ``cook`` verb finds it) and an
:class:`ApplianceComponent` declaring the categories it unlocks.

The cooking pack stays deterministic: the categories a character can cook are the union of
every reachable appliance's categories, computed purely from world state.
"""

from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    reachable_ids,
    spawn_entity,
)
from bunnyland.core.ecs import entity_name
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .components import StoveComponent
from .recipes import APPLIANCE_RECIPES, Recipe

#: appliance kind -> the recipe categories it unlocks.
APPLIANCE_CATEGORIES: dict[str, tuple[str, ...]] = {
    "grill": ("grilled",),
    "smoker": ("smoked",),
    "oven": ("baking",),
}

#: recipe category -> the appliance kind that cooks it (for friendly rejection text).
CATEGORY_APPLIANCE: dict[str, str] = {
    category: kind for kind, categories in APPLIANCE_CATEGORIES.items() for category in categories
}


@dataclass(frozen=True)
class ApplianceComponent(Component):
    """Marks a specialised cooker and the recipe categories it unlocks."""

    kind: str = "oven"
    categories: tuple[str, ...] = ()


def appliance_categories(kind: str) -> tuple[str, ...]:
    """Return the categories an appliance ``kind`` unlocks (empty for an unknown kind)."""
    return APPLIANCE_CATEGORIES.get(kind, ())


def unlocked_categories(world: World, character: Entity) -> frozenset[str]:
    """Every recipe category unlocked by an appliance the character can reach."""
    categories: set[str] = set()
    for entity_id in reachable_ids(world, character):
        entity = world.get_entity(entity_id)
        if entity.has_component(ApplianceComponent):
            categories.update(entity.get_component(ApplianceComponent).categories)
    return frozenset(categories)


def unlocked_appliance_recipes(categories: frozenset[str]) -> tuple[Recipe, ...]:
    """The appliance recipes whose category is in ``categories`` (simplest to richest)."""
    return tuple(recipe for recipe in APPLIANCE_RECIPES if recipe.category in categories)


def spawn_appliance(
    world: World,
    *,
    kind: str = "oven",
    room_id=None,
    name: str | None = None,
    heat: str = "wood",
) -> Entity:
    """Spawn an appliance fixture (also a stove), optionally placed in ``room_id``."""
    appliance = spawn_entity(
        world,
        [
            IdentityComponent(name=name or kind, kind="item", tags=("hearthsim", "appliance")),
            StoveComponent(heat=heat),
            ApplianceComponent(kind=kind, categories=appliance_categories(kind)),
            PortableComponent(),
            HoldableComponent(slot="hand"),
        ],
    )
    if room_id is not None and world.has_entity(room_id):
        world.get_entity(room_id).add_relationship(
            Contains(mode=ContainmentMode.ROOM_CONTENT), appliance.id
        )
    return appliance


def appliance_fragments(world: World, character: Entity) -> list[str]:
    """Describe reachable appliances and the extra dishes they unlock."""
    lines: list[str] = []
    for entity_id in reachable_ids(world, character):
        entity = world.get_entity(entity_id)
        if not entity.has_component(ApplianceComponent):
            continue
        appliance = entity.get_component(ApplianceComponent)
        name = entity_name(entity, appliance.kind)
        dishes = ", ".join(
            recipe.name for recipe in unlocked_appliance_recipes(frozenset(appliance.categories))
        )
        if dishes:
            lines.append(f"A {name} here can cook {dishes}.")
        else:
            lines.append(f"A {name} here is ready for cooking.")
    return sorted(dict.fromkeys(lines))


__all__ = [
    "APPLIANCE_CATEGORIES",
    "CATEGORY_APPLIANCE",
    "ApplianceComponent",
    "appliance_categories",
    "appliance_fragments",
    "spawn_appliance",
    "unlocked_appliance_recipes",
    "unlocked_categories",
]
