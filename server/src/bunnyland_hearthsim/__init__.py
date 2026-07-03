"""Out-of-tree Bunnyland plugin: a cooking & meals pack (recipes, stoves, buffs, feasts)."""

from .components import (
    BuffComponent,
    FreshnessComponent,
    IngredientComponent,
    MealComponent,
    StoveComponent,
)
from .cooking import (
    COOK_ACTION_DEFINITIONS,
    COOK_ACTION_HANDLERS,
    CookHandler,
    MealCookedEvent,
)
from .enrichment import HearthWorldgenHook
from .feasts import FeastEnjoyedEvent, diners_in_room, share_feast
from .fragments import hearthsim_fragments
from .freshness import (
    FoodSpoiledEvent,
    SpoilageConsequence,
    freshness_state,
)
from .install import install_hearthsim
from .meals import (
    MEAL_ACTION_DEFINITIONS,
    MEAL_ACTION_HANDLERS,
    BuffAppliedEvent,
    BuffExpiredEvent,
    BuffExpiryConsequence,
    EatMealHandler,
    MealEatenEvent,
)
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import spawn_ingredient, spawn_meal, spawn_stove
from .recipes import RECIPES, Recipe, find_recipe, match_recipe, recipe_by_name
from .spatial import holder_of, room_of

__all__ = [
    "COOK_ACTION_DEFINITIONS",
    "COOK_ACTION_HANDLERS",
    "MEAL_ACTION_DEFINITIONS",
    "MEAL_ACTION_HANDLERS",
    "PLUGIN_ID",
    "RECIPES",
    "BuffAppliedEvent",
    "BuffComponent",
    "BuffExpiredEvent",
    "BuffExpiryConsequence",
    "CookHandler",
    "EatMealHandler",
    "FeastEnjoyedEvent",
    "FoodSpoiledEvent",
    "FreshnessComponent",
    "HearthWorldgenHook",
    "IngredientComponent",
    "MealComponent",
    "MealCookedEvent",
    "MealEatenEvent",
    "Recipe",
    "SpoilageConsequence",
    "StoveComponent",
    "bunnyland_plugins",
    "diners_in_room",
    "find_recipe",
    "freshness_state",
    "hearthsim_fragments",
    "holder_of",
    "install_hearthsim",
    "match_recipe",
    "plugin",
    "recipe_by_name",
    "room_of",
    "share_feast",
    "spawn_ingredient",
    "spawn_meal",
    "spawn_stove",
]
