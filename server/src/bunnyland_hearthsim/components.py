"""Cooking-pack components: ingredients, stoves, meals, meal buffs, and freshness.

All state is immutable pydantic-dataclass :class:`~relics.Component` values. Mutate by
building a new value (usually via :func:`dataclasses.replace`) and swapping it in with
``replace_component`` — never mutate a field in place.

The pack is deliberately small in components and rich in behaviour: recipes are a plain
module-level registry (see :mod:`bunnyland_hearthsim.recipes`), while these components mark
the *things* the mechanics act on.
"""

from __future__ import annotations

from pydantic.dataclasses import dataclass
from relics import Component

# --------------------------------------------------------------------------------------
# Ingredients — the raw inputs a recipe consumes
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class IngredientComponent(Component):
    """Marks an item as a cooking ingredient carrying one or more recipe tags.

    A carrot might be ``("vegetable",)``; a soup bone ``("meat", "broth")``. Recipes match
    on these tags, so a single ingredient can satisfy several roles.
    """

    tags: tuple[str, ...] = ()


# --------------------------------------------------------------------------------------
# Stoves — the appliance a character cooks at
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class StoveComponent(Component):
    """Marks a room fixture (or portable camp stove) that the ``cook`` verb runs at."""

    heat: str = "gas"


# --------------------------------------------------------------------------------------
# Meals — the cooked output of a recipe
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class MealComponent(Component):
    """A finished dish. Eating it restores hunger and applies a timed buff."""

    name: str = "meal"
    buff: str = "well-fed"
    buff_magnitude: float = 1.0
    buff_duration: int = 14400  # game-seconds the buff lasts once eaten (4 game hours)
    satiety: float = 30.0
    nutrition: float = 20.0


# --------------------------------------------------------------------------------------
# Buffs — the timed "moodlet" a good meal grants the eater
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class BuffComponent(Component):
    """A timed positive status a character carries after eating a meal.

    Only one buff is held at a time (one component of a type per entity); eating another
    meal refreshes it. :class:`~bunnyland_hearthsim.meals.BuffExpiryConsequence` removes it
    once ``expires_at_epoch`` is reached.
    """

    name: str = "well-fed"
    magnitude: float = 1.0
    started_at_epoch: int = 0
    expires_at_epoch: int = 0


# --------------------------------------------------------------------------------------
# Freshness — food that decays over time
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FreshnessComponent(Component):
    """Tracks how long a food has left before it spoils.

    :class:`~bunnyland_hearthsim.freshness.SpoilageConsequence` flips ``spoiled`` once the
    food is older than ``spoils_after`` game-seconds. A spoiled meal grants no buff and is
    unpleasant to eat.
    """

    cooked_at_epoch: int = 0
    spoils_after: int = 86400  # one game day
    spoiled: bool = False


__all__ = [
    "BuffComponent",
    "FreshnessComponent",
    "IngredientComponent",
    "MealComponent",
    "StoveComponent",
]
