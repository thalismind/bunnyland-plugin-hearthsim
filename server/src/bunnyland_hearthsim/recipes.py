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
    """A dish: the ingredient tags it needs and the meal it yields.

    ``category`` groups dishes for appliances and contests. The default ``"general"`` is
    what any plain stove can cook; the appliance categories (``"grilled"``, ``"smoked"``,
    ``"baking"``) are only cookable when a matching appliance is within reach — see
    :mod:`bunnyland_hearthsim.appliances`.
    """

    name: str
    required_tags: tuple[str, ...]
    buff: str = "well-fed"
    buff_magnitude: float = 1.0
    buff_duration: int = 14400  # game-seconds the meal buff lasts (4 game hours)
    satiety: float = 30.0
    nutrition: float = 20.0
    spoils_after: int = 86400  # one game day before the cooked meal spoils
    category: str = "general"


#: How long a preserved food keeps before spoiling — two game days, twice a normal meal.
PRESERVE_SPOILS_AFTER = 172800

#: The pack's cookbook, authored grouped by category for readability. The public ``RECIPES``
#: tuple below is derived from this by a deterministic ``(satiety, name)`` sort, so the
#: registry is always ordered from simplest to richest. ``find_recipe`` prefers the first
#: recipe whose tags can be satisfied, so a sparse pantry yields a light dish while a fuller
#: pantry unlocks the heartier ones.
#:
#: Ordering note: no recipe may be makeable from a *subset* of ``{vegetable, meat, broth}``
#: and sort before ``hearty stew``, or it would shadow the stew. This is why, e.g., the
#: vegetable broth also requires ``herb`` — a plain ``(vegetable, broth)`` dish would steal
#: the stew's ingredients.
_CATALOGUE: tuple[Recipe, ...] = (
    # ---- Breakfasts -------------------------------------------------------------------
    Recipe("porridge", ("grain", "dairy"), buff="warmed", satiety=24.0, nutrition=22.0),
    Recipe(
        "berry parfait",
        ("berry", "dairy", "grain"),
        buff="refreshed",
        satiety=22.0,
        nutrition=26.0,
    ),
    Recipe(
        "fruit muesli",
        ("grain", "fruit", "nut"),
        buff="refreshed",
        satiety=26.0,
        nutrition=28.0,
    ),
    Recipe(
        "veggie scramble",
        ("egg", "egg", "vegetable"),
        buff="well-fed",
        satiety=28.0,
        nutrition=26.0,
    ),
    Recipe(
        "breakfast hash",
        ("root", "egg", "herb"),
        buff="nourished",
        satiety=32.0,
        nutrition=28.0,
        buff_duration=16200,
    ),
    Recipe(
        "pancake stack",
        ("grain", "egg", "sweet"),
        buff="delighted",
        satiety=30.0,
        nutrition=20.0,
        buff_duration=18000,
    ),
    # ---- Soups & stews ----------------------------------------------------------------
    Recipe(
        "vegetable broth",
        ("vegetable", "broth", "herb"),
        buff="comforted",
        satiety=24.0,
        nutrition=22.0,
        buff_duration=16200,
    ),
    Recipe(
        "mushroom soup",
        ("mushroom", "broth", "dairy"),
        buff="comforted",
        satiety=30.0,
        nutrition=24.0,
        buff_duration=18000,
    ),
    Recipe(
        "chicken soup",
        ("poultry", "broth", "vegetable"),
        buff="comforted",
        satiety=38.0,
        nutrition=32.0,
        buff_duration=21600,
    ),
    Recipe(
        "fish chowder",
        ("fish", "dairy", "root"),
        buff="hearty",
        satiety=40.0,
        nutrition=33.0,
        buff_duration=21600,
    ),
    Recipe(
        "lentil stew",
        ("bean", "vegetable", "broth"),
        buff="nourished",
        satiety=40.0,
        nutrition=36.0,
        buff_duration=21600,
    ),
    Recipe(
        "bean chili",
        ("bean", "meat", "spice"),
        buff="hearty",
        satiety=42.0,
        nutrition=34.0,
        buff_duration=21600,
    ),
    Recipe(
        "hearty stew",
        ("vegetable", "meat", "broth"),
        buff="hearty",
        satiety=45.0,
        nutrition=35.0,
        buff_duration=21600,
    ),
    # ---- Breads & baked goods ---------------------------------------------------------
    Recipe("flatbread", ("grain", "herb"), buff="well-fed", satiety=22.0, nutrition=20.0),
    Recipe("bread loaf", ("grain", "grain"), buff="well-fed", satiety=25.0, nutrition=22.0),
    Recipe("cheese scone", ("grain", "cheese"), buff="well-fed", satiety=26.0, nutrition=24.0),
    Recipe(
        "dinner rolls",
        ("grain", "dairy", "egg"),
        buff="well-fed",
        satiety=28.0,
        nutrition=24.0,
    ),
    Recipe(
        "herb focaccia",
        ("grain", "grain", "herb"),
        buff="well-fed",
        satiety=30.0,
        nutrition=26.0,
        buff_duration=16200,
    ),
    # ---- Roasts & mains ---------------------------------------------------------------
    Recipe("grilled fish", ("fish",), buff="well-fed", satiety=30.0, nutrition=28.0),
    Recipe(
        "stuffed peppers",
        ("vegetable", "grain", "cheese"),
        buff="satisfied",
        satiety=36.0,
        nutrition=32.0,
        buff_duration=21600,
    ),
    Recipe(
        "fish tacos",
        ("fish", "grain", "vegetable"),
        buff="satisfied",
        satiety=38.0,
        nutrition=34.0,
        buff_duration=21600,
    ),
    Recipe(
        "mushroom risotto",
        ("mushroom", "grain", "cheese"),
        buff="satisfied",
        satiety=38.0,
        nutrition=32.0,
        buff_duration=21600,
    ),
    Recipe(
        "grilled steak",
        ("meat", "spice"),
        buff="stuffed",
        satiety=44.0,
        nutrition=38.0,
        buff_duration=28800,
    ),
    Recipe(
        "roast chicken",
        ("poultry", "herb"),
        buff="stuffed",
        satiety=46.0,
        nutrition=38.0,
        buff_duration=28800,
    ),
    Recipe(
        "meatball pasta",
        ("meat", "grain", "herb"),
        buff="stuffed",
        satiety=46.0,
        nutrition=36.0,
        buff_duration=28800,
    ),
    Recipe(
        "seafood paella",
        ("seafood", "grain", "vegetable"),
        buff="stuffed",
        satiety=48.0,
        nutrition=40.0,
        buff_duration=28800,
    ),
    Recipe(
        "roast dinner",
        ("meat", "vegetable", "vegetable"),
        buff="stuffed",
        satiety=50.0,
        nutrition=40.0,
        buff_duration=28800,
    ),
    # ---- Salads & sides ---------------------------------------------------------------
    Recipe(
        "fruit salad",
        ("fruit", "fruit", "citrus"),
        buff="refreshed",
        satiety=20.0,
        nutrition=24.0,
    ),
    Recipe(
        "garden salad",
        ("vegetable", "vegetable"),
        buff="refreshed",
        satiety=20.0,
        nutrition=25.0,
    ),
    Recipe(
        "spring salad",
        ("vegetable", "vegetable", "herb"),
        buff="refreshed",
        satiety=22.0,
        nutrition=26.0,
    ),
    Recipe(
        "caprese",
        ("vegetable", "cheese", "herb"),
        buff="refreshed",
        satiety=24.0,
        nutrition=26.0,
    ),
    Recipe(
        "bean salad",
        ("bean", "vegetable", "herb"),
        buff="refreshed",
        satiety=26.0,
        nutrition=28.0,
    ),
    Recipe(
        "roasted roots",
        ("root", "root", "herb"),
        buff="nourished",
        satiety=30.0,
        nutrition=28.0,
        buff_duration=16200,
    ),
    # ---- Desserts & sweets ------------------------------------------------------------
    Recipe(
        "nut brittle",
        ("nut", "sweet"),
        buff="cheered",
        satiety=18.0,
        nutrition=16.0,
    ),
    Recipe(
        "custard",
        ("dairy", "egg", "sweet"),
        buff="delighted",
        satiety=26.0,
        nutrition=18.0,
        buff_duration=18000,
    ),
    Recipe(
        "chocolate mousse",
        ("chocolate", "dairy", "egg"),
        buff="delighted",
        satiety=28.0,
        nutrition=16.0,
        buff_duration=18000,
    ),
    Recipe(
        "berry tart",
        ("berry", "grain", "sweet"),
        buff="delighted",
        satiety=30.0,
        nutrition=18.0,
        buff_duration=18000,
    ),
    Recipe(
        "honey cake",
        ("grain", "egg", "honey"),
        buff="delighted",
        satiety=32.0,
        nutrition=18.0,
        buff_duration=18000,
    ),
    Recipe(
        "apple crumble",
        ("fruit", "grain", "honey"),
        buff="delighted",
        satiety=34.0,
        nutrition=20.0,
        buff_duration=18000,
    ),
    Recipe(
        "fruit pie",
        ("fruit", "grain", "sweet"),
        buff="delighted",
        satiety=35.0,
        nutrition=20.0,
        buff_duration=18000,
    ),
    # ---- Drinks -----------------------------------------------------------------------
    Recipe(
        "herbal tea",
        ("tea", "herb"),
        buff="refreshed",
        satiety=8.0,
        nutrition=6.0,
        buff_duration=7200,
    ),
    Recipe(
        "fresh lemonade",
        ("citrus", "sweet"),
        buff="refreshed",
        satiety=10.0,
        nutrition=10.0,
        buff_duration=7200,
    ),
    Recipe(
        "spiced cider",
        ("fruit", "spice"),
        buff="warmed",
        satiety=12.0,
        nutrition=12.0,
        buff_duration=10800,
    ),
    Recipe(
        "hot cocoa",
        ("chocolate", "dairy", "sweet"),
        buff="comforted",
        satiety=14.0,
        nutrition=14.0,
        buff_duration=10800,
    ),
    Recipe(
        "berry smoothie",
        ("berry", "dairy", "honey"),
        buff="refreshed",
        satiety=16.0,
        nutrition=20.0,
        buff_duration=10800,
    ),
    # ---- Preserves (keep far longer than a fresh meal) --------------------------------
    Recipe(
        "berry jam",
        ("berry", "sweet"),
        buff="content",
        satiety=12.0,
        nutrition=14.0,
        buff_duration=16200,
        spoils_after=PRESERVE_SPOILS_AFTER,
    ),
    Recipe(
        "fruit preserve",
        ("fruit", "sweet"),
        buff="content",
        satiety=14.0,
        nutrition=16.0,
        buff_duration=16200,
        spoils_after=PRESERVE_SPOILS_AFTER,
    ),
    Recipe(
        "pickled vegetables",
        ("vegetable", "spice"),
        buff="content",
        satiety=14.0,
        nutrition=16.0,
        buff_duration=16200,
        spoils_after=PRESERVE_SPOILS_AFTER,
    ),
    Recipe(
        "smoked fish",
        ("fish", "spice"),
        buff="sated",
        satiety=20.0,
        nutrition=22.0,
        buff_duration=16200,
        spoils_after=PRESERVE_SPOILS_AFTER,
    ),
)

#: The public cookbook: the catalogue sorted deterministically from simplest to richest.
RECIPES: tuple[Recipe, ...] = tuple(
    sorted(_CATALOGUE, key=lambda recipe: (recipe.satiety, recipe.name))
)

#: Fast membership set for validating a caller-requested recipe name.
RECIPE_NAMES: frozenset[str] = frozenset(recipe.name for recipe in RECIPES)

#: Appliance-gated recipes (mechanic 8). Each carries an appliance ``category`` and can only
#: be cooked when a matching appliance (grill / smoker / oven) is within reach. They are kept
#: out of :data:`RECIPES` so a plain stove still cooks the whole base cookbook and nothing
#: more; :func:`find_recipe` folds in only the unlocked ones via its ``extra`` argument.
_APPLIANCE_CATALOGUE: tuple[Recipe, ...] = (
    # ---- Grill (open flame, char) -----------------------------------------------------
    Recipe(
        "grilled skewers",
        ("meat", "vegetable", "herb"),
        buff="stuffed",
        satiety=44.0,
        nutrition=38.0,
        buff_duration=28800,
        category="grilled",
    ),
    Recipe(
        "charred peppers",
        ("vegetable", "vegetable", "spice"),
        buff="satisfied",
        satiety=28.0,
        nutrition=26.0,
        buff_duration=18000,
        category="grilled",
    ),
    # ---- Smoker (slow, preserving) ----------------------------------------------------
    Recipe(
        "smoked brisket",
        ("meat", "spice", "herb"),
        buff="stuffed",
        satiety=48.0,
        nutrition=40.0,
        buff_duration=28800,
        spoils_after=PRESERVE_SPOILS_AFTER,
        category="smoked",
    ),
    Recipe(
        "smoked trout",
        ("fish", "herb", "spice"),
        buff="sated",
        satiety=32.0,
        nutrition=30.0,
        buff_duration=21600,
        spoils_after=PRESERVE_SPOILS_AFTER,
        category="smoked",
    ),
    # ---- Oven (wood-fired baking) -----------------------------------------------------
    Recipe(
        "wood-fired loaf",
        ("grain", "grain", "seed"),
        buff="well-fed",
        satiety=30.0,
        nutrition=28.0,
        buff_duration=18000,
        category="baking",
    ),
    Recipe(
        "baked casserole",
        ("root", "cheese", "broth"),
        buff="hearty",
        satiety=42.0,
        nutrition=36.0,
        buff_duration=21600,
        category="baking",
    ),
)

#: Appliance recipes, ordered simplest to richest like :data:`RECIPES`.
APPLIANCE_RECIPES: tuple[Recipe, ...] = tuple(
    sorted(_APPLIANCE_CATALOGUE, key=lambda recipe: (recipe.satiety, recipe.name))
)

#: Fast membership set for validating a caller-requested appliance recipe name.
APPLIANCE_RECIPE_NAMES: frozenset[str] = frozenset(r.name for r in APPLIANCE_RECIPES)


def appliance_recipe_by_name(name: str) -> Recipe | None:
    """Return the appliance recipe with ``name``, or ``None`` if there is none."""
    for recipe in APPLIANCE_RECIPES:
        if recipe.name == name:
            return recipe
    return None


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
    extra: Sequence[Recipe] = (),
) -> tuple[Recipe, list[EntityId]] | None:
    """Find the best makeable recipe for ``ingredients`` (optionally forcing ``name``).

    The base :data:`RECIPES` are always searched first (simplest to richest); ``extra``
    recipes — the appliance recipes unlocked by a reachable appliance — are appended after,
    so a plain stove keeps its exact v1 behaviour and appliance dishes only surface when
    their appliance is present.

    Returns ``(recipe, consumed_ingredient_ids)`` or ``None`` when nothing can be cooked.
    """
    available = list(ingredients)
    pool = (*RECIPES, *extra)
    candidates = pool if name is None else tuple(r for r in pool if r.name == name)
    for recipe in candidates:
        used = match_recipe(recipe, available)
        if used is not None:
            return recipe, used
    return None


__all__ = [
    "APPLIANCE_RECIPES",
    "APPLIANCE_RECIPE_NAMES",
    "PRESERVE_SPOILS_AFTER",
    "RECIPES",
    "RECIPE_NAMES",
    "Recipe",
    "appliance_recipe_by_name",
    "find_recipe",
    "match_recipe",
    "recipe_by_name",
]
