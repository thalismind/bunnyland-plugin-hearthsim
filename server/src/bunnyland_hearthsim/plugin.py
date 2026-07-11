"""Bunnyland plugin entrypoint for the out-of-tree hearthsim cooking pack."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    DependencyContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .appliances import ApplianceComponent, appliance_fragments
from .catering import (
    CATERING_ACTION_DEFINITIONS,
    CATERING_ACTION_HANDLERS,
    CateredFor,
    MealCateredEvent,
)
from .components import (
    BuffComponent,
    FreshnessComponent,
    IngredientComponent,
    MealComponent,
    StoveComponent,
)
from .cooking import COOK_ACTION_DEFINITIONS, COOK_ACTION_HANDLERS, MealCookedEvent
from .enrichment import HearthGenerationEnricher
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
from .skill import (
    CookingSkillComponent,
    CookingSkillImprovedEvent,
    cooking_skill_fragments,
)
from .storyteller import (
    CommunalFeastCalledEvent,
    FeastStorytellerComponent,
    feast_storyteller_fragments,
    install_storyteller,
)

PLUGIN_ID = "bunnyland.hearthsim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Hearthsim",
        version="0.2.0",
        default_enabled=True,
        # Soft food-chain partners: hearthsim runs standalone, but ingredients flow in from
        # the gatherers (wild/angler/aqua/garden) and its meals flow out to the festival
        # feast. All are optional — declared here, never hard-imported.
        dependencies=DependencyContribution(
            recommends=(
                "bunnyland.wildsim",
                "bunnyland.anglersim",
                "bunnyland.aquasim",
                "bunnyland.gardensim",
                "bunnyland.festivalsim",
            ),
        ),
        ecs=EcsContribution(
            components=(
                IngredientComponent,
                StoveComponent,
                MealComponent,
                BuffComponent,
                FreshnessComponent,
                CookingSkillComponent,
                ApplianceComponent,
                FeastStorytellerComponent,
            ),
            edges=(CateredFor,),
        ),
        commands=CommandContribution(
            action_handlers=(
                *COOK_ACTION_HANDLERS,
                *MEAL_ACTION_HANDLERS,
                *CATERING_ACTION_HANDLERS,
            ),
            action_definitions=(
                *COOK_ACTION_DEFINITIONS,
                *MEAL_ACTION_DEFINITIONS,
                *CATERING_ACTION_DEFINITIONS,
            ),
            typed_events=(
                MealCookedEvent,
                MealEatenEvent,
                BuffAppliedEvent,
                BuffExpiredEvent,
                FoodSpoiledEvent,
                FeastEnjoyedEvent,
                CookingSkillImprovedEvent,
                MealCateredEvent,
                CommunalFeastCalledEvent,
            ),
        ),
        runtime=RuntimeContribution(
            service_factories=(install_hearthsim, install_storyteller),
        ),
        content=ContentContribution(
            prompt_fragments=(
                hearthsim_fragments,
                cooking_skill_fragments,
                appliance_fragments,
                feast_storyteller_fragments,
            ),
            generation_enrichers=(HearthGenerationEnricher(),),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
