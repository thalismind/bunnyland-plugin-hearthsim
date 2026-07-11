from __future__ import annotations

import pytest
from relics import EntityId

from bunnyland_hearthsim.recipes import (
    RECIPE_NAMES,
    RECIPES,
    find_recipe,
    match_recipe,
    recipe_by_name,
)


def _pantry(*items):
    """Build a deterministic ``(id, tags)`` list from ``(seq, tags)`` pairs."""
    return [(EntityId(prefab="entity", sequence=seq), frozenset(tags)) for seq, tags in items]


def _minimal_pantry(recipe):
    """One distinct single-tag ingredient per required tag slot of ``recipe``."""
    return [
        (EntityId(prefab="ingredient", sequence=index), frozenset({tag}))
        for index, tag in enumerate(recipe.required_tags)
    ]


def test_registry_names_match_lookup():
    assert RECIPE_NAMES == frozenset(recipe.name for recipe in RECIPES)
    for recipe in RECIPES:
        assert recipe_by_name(recipe.name) is recipe


def test_recipe_by_name_returns_none_for_unknown():
    assert recipe_by_name("moon cheese") is None


def test_find_prefers_first_makeable_recipe():
    # Two vegetables satisfy the very first recipe (garden salad).
    pantry = _pantry((1, ("vegetable",)), (2, ("vegetable",)))
    recipe, used = find_recipe(pantry)
    assert recipe.name == "garden salad"
    assert len(used) == 2


def test_find_matches_multi_tag_recipe():
    pantry = _pantry((1, ("vegetable",)), (2, ("meat",)), (3, ("broth",)))
    recipe, used = find_recipe(pantry)
    assert recipe.name == "hearty stew"
    assert set(used) == {p[0] for p in pantry}


def test_single_ingredient_covers_multiple_tags():
    # One item tagged both meat and broth cannot fill two *distinct* stew slots...
    pantry = _pantry((1, ("meat", "broth")), (2, ("vegetable",)))
    assert find_recipe(pantry, name="hearty stew") is None
    # ...but it can satisfy grilled fish? No — needs fish. It has no makeable recipe here
    # except none, so a general search returns None too.
    assert find_recipe(pantry) is None


def test_find_returns_none_without_ingredients():
    assert find_recipe([]) is None


def test_forced_recipe_requires_its_tags():
    pantry = _pantry((1, ("vegetable",)))
    assert find_recipe(pantry, name="garden salad") is None  # needs two vegetables
    pantry2 = _pantry((1, ("vegetable",)), (2, ("vegetable",)))
    recipe, used = find_recipe(pantry2, name="garden salad")
    assert recipe.name == "garden salad"
    assert len(used) == 2


def test_catalogue_is_wide_and_uniquely_named():
    # The expanded cookbook spans many dishes; every entry is uniquely named.
    assert len(RECIPES) >= 35
    names = [recipe.name for recipe in RECIPES]
    assert len(names) == len(set(names))


def test_registry_is_sorted_simplest_to_richest():
    # ``RECIPES`` is derived by a deterministic (satiety, name) sort.
    keys = [(recipe.satiety, recipe.name) for recipe in RECIPES]
    assert keys == sorted(keys)


def test_every_recipe_has_a_distinct_required_tag_multiset():
    seen = {tuple(sorted(recipe.required_tags)) for recipe in RECIPES}
    assert len(seen) == len(RECIPES)


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda recipe: recipe.name)
def test_every_recipe_is_cookable_from_its_tags(recipe):
    # A minimal pantry (one distinct ingredient per required tag) makes exactly this recipe.
    result = find_recipe(_minimal_pantry(recipe), name=recipe.name)
    assert result is not None
    matched, used = result
    assert matched is recipe
    assert len(used) == len(recipe.required_tags)


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda recipe: recipe.name)
def test_recipe_needs_all_required_tags(recipe):
    # Dropping the last required ingredient leaves the recipe unmakeable (forced by name).
    short = _minimal_pantry(recipe)[:-1]
    assert find_recipe(short, name=recipe.name) is None


def test_match_recipe_is_deterministic_by_order():
    recipe = recipe_by_name("garden salad")
    pantry = _pantry((5, ("vegetable",)), (2, ("vegetable",)), (9, ("vegetable",)))
    # match_recipe consumes in the given order; find_recipe sorts upstream.
    used = match_recipe(recipe, pantry)
    assert used == [pantry[0][0], pantry[1][0]]
