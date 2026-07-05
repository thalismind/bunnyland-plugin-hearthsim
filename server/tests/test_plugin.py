from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_hearthsim import (
    ApplianceComponent,
    BuffComponent,
    CateredFor,
    CommunalFeastCalledEvent,
    CookingSkillComponent,
    CookingSkillImprovedEvent,
    FeastStorytellerComponent,
    FreshnessComponent,
    HearthWorldgenHook,
    IngredientComponent,
    MealCateredEvent,
    MealComponent,
    StoveComponent,
    appliance_fragments,
    cooking_skill_fragments,
    feast_storyteller_fragments,
    hearthsim_fragments,
)
from bunnyland_hearthsim.plugin import PLUGIN_ID


def test_plugin_loads_with_module_qualified_id():
    plugins = load_modules(["bunnyland_hearthsim"])
    assert [p.id for p in plugins] == [PLUGIN_ID]


def test_plugin_is_bumped_to_v2():
    assert load_modules(["bunnyland_hearthsim"])[0].version == "0.2.0"


def test_plugin_declares_its_contributions():
    plugin = load_modules(["bunnyland_hearthsim"])[0]
    for component in (
        IngredientComponent,
        StoveComponent,
        MealComponent,
        BuffComponent,
        FreshnessComponent,
        CookingSkillComponent,
        ApplianceComponent,
        FeastStorytellerComponent,
    ):
        assert component in plugin.ecs.components
    assert CateredFor in plugin.ecs.edges
    assert HearthWorldgenHook in plugin.content.worldgen_hooks
    for provider in (
        hearthsim_fragments,
        cooking_skill_fragments,
        appliance_fragments,
        feast_storyteller_fragments,
    ):
        assert provider in plugin.content.prompt_fragments


def test_plugin_declares_v2_events():
    plugin = load_modules(["bunnyland_hearthsim"])[0]
    for event in (CookingSkillImprovedEvent, MealCateredEvent, CommunalFeastCalledEvent):
        assert event in plugin.commands.typed_events


def test_plugin_recommends_food_chain_partners():
    plugin = load_modules(["bunnyland_hearthsim"])[0]
    recommends = plugin.dependencies.recommends
    assert "bunnyland.wildsim" in recommends
    assert "bunnyland.festivalsim" in recommends


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_hearthsim"]), actor)
    assert applied[0].id == PLUGIN_ID
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"cook", "eat-meal", "cater"} <= command_types
    # The service factories seeded the communal-feast storyteller marker.
    markers = list(
        actor.world.query().with_all([FeastStorytellerComponent]).execute_entities()
    )
    assert len(markers) == 1
