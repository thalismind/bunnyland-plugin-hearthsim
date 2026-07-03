"""Recipe registry and deterministic ingredient matching (mechanic 1).

A recipe maps a list of required ingredient *tags* to a finished meal. Matching is a plain
module-level table rather than a component: recipes are shared knowledge, not per-entity
state. Matching is deterministic — given a fixed, sorted list of available ingredients the
same recipe and the same ingredient items are always chosen — so cooking never depends on
iteration order, randomness, or wall-clock time.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from pydantic.dataclasses import dataclass
from relics import EntityId


@dataclass(frozen=True)
class Recipe:
    """A dish: the ingredient tags it needs and the meal it yields."""

    name: str
    required_tags: tuple[str, ...]
    buff: str = "well-fed"
    buff_magnitude: float = 1.0
    buff_duration: int = 14400  # game-seconds the meal buff lasts (4 game hours)
    satiety: float = 30.0
    nutrition: float = 20.0
    spoils_after: int = 86400  # one game day before the cooked meal spoils


#: The pack's cookbook. Ordered from simplest to richest; ``find_recipe`` prefers the first
#: recipe whose tags can be satisfied, so a fuller pantry yields a heartier meal.
RECIPES: tuple[Recipe, ...] = (
    Recipe(
        "garden salad",
        ("vegetable", "vegetable"),
        buff="refreshed",
        satiety=20.0,
        nutrition=25.0,
    ),
    Recipe("bread loaf", ("grain", "grain"), buff="well-fed", satiety=25.0, nutrition=22.0),
    Recipe("grilled fish", ("fish",), buff="well-fed", satiety=30.0, nutrition=28.0),
    Recipe("cheese omelet", ("egg", "dairy"), buff="well-fed", satiety=28.0, nutrition=24.0),
    Recipe(
        "fruit pie",
        ("fruit", "grain", "sweet"),
        buff="delighted",
        satiety=35.0,
        nutrition=20.0,
        buff_duration=18000,
    ),
    Recipe(
        "hearty stew",
        ("vegetable", "meat", "broth"),
        buff="hearty",
        satiety=45.0,
        nutrition=35.0,
        buff_duration=21600,
    ),
    Recipe(
        "roast dinner",
        ("meat", "vegetable", "vegetable"),
        buff="stuffed",
        satiety=50.0,
        nutrition=40.0,
        buff_duration=28800,
    ),
)

#: Fast membership set for validating a caller-requested recipe name.
RECIPE_NAMES: frozenset[str] = frozenset(recipe.name for recipe in RECIPES)


def recipe_by_name(name: str) -> Recipe | None:
    """Return the recipe with ``name``, or ``None`` if it is not in the cookbook."""
    for recipe in RECIPES:
        if recipe.name == name:
            return recipe
    return None


def match_recipe(
    recipe: Recipe, ingredients: Sequence[tuple[EntityId, frozenset[str]]]
) -> list[EntityId] | None:
    """Return the ingredient ids satisfying ``recipe``, or ``None`` if it cannot be made.

    Each required tag must be covered by a *distinct* ingredient carrying that tag. Ties are
    broken by the incoming (sorted) order, so the result is deterministic.
    """
    remaining = list(ingredients)
    used: list[EntityId] = []
    for tag in recipe.required_tags:
        chosen = next((index for index, (_id, tags) in enumerate(remaining) if tag in tags), None)
        if chosen is None:
            return None
        used.append(remaining.pop(chosen)[0])
    return used


def find_recipe(
    ingredients: Iterable[tuple[EntityId, frozenset[str]]],
    *,
    name: str | None = None,
) -> tuple[Recipe, list[EntityId]] | None:
    """Find the best makeable recipe for ``ingredients`` (optionally forcing ``name``).

    Returns ``(recipe, consumed_ingredient_ids)`` or ``None`` when nothing can be cooked.
    """
    available = list(ingredients)
    candidates = RECIPES if name is None else tuple(r for r in RECIPES if r.name == name)
    for recipe in candidates:
        used = match_recipe(recipe, available)
        if used is not None:
            return recipe, used
    return None


__all__ = [
    "RECIPES",
    "RECIPE_NAMES",
    "Recipe",
    "find_recipe",
    "match_recipe",
    "recipe_by_name",
]
