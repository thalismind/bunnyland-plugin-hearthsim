"""Bunnyland plugin entrypoint for the out-of-tree hearthsim cooking pack."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .components import (
    BuffComponent,
    FreshnessComponent,
    IngredientComponent,
    MealComponent,
    StoveComponent,
)
from .cooking import COOK_ACTION_DEFINITIONS, COOK_ACTION_HANDLERS, MealCookedEvent
from .enrichment import HearthWorldgenHook
from .feasts import FeastEnjoyedEvent
from .fragments import hearthsim_fragments
from .freshness import FoodSpoiledEvent
from .install import install_hearthsim
from .meals import (
    MEAL_ACTION_DEFINITIONS,
    MEAL_ACTION_HANDLERS,
    BuffAppliedEvent,
    BuffExpiredEvent,
    MealEatenEvent,
)

PLUGIN_ID = "bunnyland_hearthsim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Hearthsim",
        version="0.1.0",
        default_enabled=True,
        ecs=EcsContribution(
            components=(
                IngredientComponent,
                StoveComponent,
                MealComponent,
                BuffComponent,
                FreshnessComponent,
            ),
        ),
        commands=CommandContribution(
            action_handlers=(*COOK_ACTION_HANDLERS, *MEAL_ACTION_HANDLERS),
            action_definitions=(*COOK_ACTION_DEFINITIONS, *MEAL_ACTION_DEFINITIONS),
            typed_events=(
                MealCookedEvent,
                MealEatenEvent,
                BuffAppliedEvent,
                BuffExpiredEvent,
                FoodSpoiledEvent,
                FeastEnjoyedEvent,
            ),
        ),
        runtime=RuntimeContribution(service_factories=(install_hearthsim,)),
        content=ContentContribution(
            prompt_fragments=(hearthsim_fragments,),
            worldgen_hooks=(HearthWorldgenHook,),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
