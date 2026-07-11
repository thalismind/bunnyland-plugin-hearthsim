"""Out-of-tree Bunnyland plugin: a cooking & meals pack (recipes, stoves, buffs, feasts).

v2 adds the headline **catering** mechanic (serving a whole room at once), a **cooking skill**
that grows with every dish, **appliances** that unlock recipe categories, and a communal-feast
**storyteller** incident — all routed through core hunger, social bonds, and the storyteller.
"""

from .appliances import (
    APPLIANCE_CATEGORIES,
    ApplianceComponent,
    appliance_categories,
    appliance_fragments,
    spawn_appliance,
    unlocked_appliance_recipes,
    unlocked_categories,
)
from .catering import (
    CATERING_ACTION_DEFINITIONS,
    CATERING_ACTION_HANDLERS,
    CateredFor,
    CaterHandler,
    MealCateredEvent,
    catering_bond,
    record_catering,
)
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
from .enrichment import HearthGenerationEnricher
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
from .recipes import (
    APPLIANCE_RECIPES,
    RECIPES,
    Recipe,
    appliance_recipe_by_name,
    find_recipe,
    match_recipe,
    recipe_by_name,
)
from .skill import (
    CookingSkillComponent,
    CookingSkillImprovedEvent,
    catering_capacity,
    cooking_skill_fragments,
    cooking_skill_of,
    grant_cooking_experience,
    meal_quality,
    skill_tier,
    skill_tier_name,
)
from .spatial import holder_of, room_of
from .storyteller import (
    CommunalFeastCalledEvent,
    CommunalFeastConsequence,
    FeastStorytellerComponent,
    feast_storyteller_fragments,
    install_storyteller,
    pending_feast_incident,
    resolve_feast_incident,
    spawn_feast_storyteller,
)

__all__ = [
    "APPLIANCE_CATEGORIES",
    "APPLIANCE_RECIPES",
    "CATERING_ACTION_DEFINITIONS",
    "CATERING_ACTION_HANDLERS",
    "COOK_ACTION_DEFINITIONS",
    "COOK_ACTION_HANDLERS",
    "MEAL_ACTION_DEFINITIONS",
    "MEAL_ACTION_HANDLERS",
    "PLUGIN_ID",
    "RECIPES",
    "ApplianceComponent",
    "BuffAppliedEvent",
    "BuffComponent",
    "BuffExpiredEvent",
    "BuffExpiryConsequence",
    "CaterHandler",
    "CateredFor",
    "CommunalFeastCalledEvent",
    "CommunalFeastConsequence",
    "CookHandler",
    "CookingSkillComponent",
    "CookingSkillImprovedEvent",
    "EatMealHandler",
    "FeastEnjoyedEvent",
    "FeastStorytellerComponent",
    "FoodSpoiledEvent",
    "FreshnessComponent",
    "HearthGenerationEnricher",
    "IngredientComponent",
    "MealCateredEvent",
    "MealComponent",
    "MealCookedEvent",
    "MealEatenEvent",
    "Recipe",
    "SpoilageConsequence",
    "StoveComponent",
    "appliance_categories",
    "appliance_fragments",
    "appliance_recipe_by_name",
    "bunnyland_plugins",
    "catering_bond",
    "catering_capacity",
    "cooking_skill_fragments",
    "cooking_skill_of",
    "diners_in_room",
    "feast_storyteller_fragments",
    "find_recipe",
    "freshness_state",
    "grant_cooking_experience",
    "hearthsim_fragments",
    "holder_of",
    "install_hearthsim",
    "install_storyteller",
    "match_recipe",
    "meal_quality",
    "pending_feast_incident",
    "plugin",
    "record_catering",
    "recipe_by_name",
    "resolve_feast_incident",
    "room_of",
    "share_feast",
    "skill_tier",
    "skill_tier_name",
    "spawn_appliance",
    "spawn_feast_storyteller",
    "spawn_ingredient",
    "spawn_meal",
    "spawn_stove",
    "unlocked_appliance_recipes",
    "unlocked_categories",
]
