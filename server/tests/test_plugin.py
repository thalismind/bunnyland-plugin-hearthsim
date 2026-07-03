from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_hearthsim import (
    BuffComponent,
    FreshnessComponent,
    HearthWorldgenHook,
    IngredientComponent,
    MealComponent,
    StoveComponent,
    hearthsim_fragments,
)
from bunnyland_hearthsim.plugin import PLUGIN_ID


def test_plugin_loads_with_module_qualified_id():
    plugins = load_modules(["bunnyland_hearthsim"])
    assert [p.id for p in plugins] == [f"bunnyland_hearthsim.{PLUGIN_ID}"]


def test_plugin_declares_its_contributions():
    plugin = load_modules(["bunnyland_hearthsim"])[0]
    for component in (
        IngredientComponent,
        StoveComponent,
        MealComponent,
        BuffComponent,
        FreshnessComponent,
    ):
        assert component in plugin.ecs.components
    assert HearthWorldgenHook in plugin.content.worldgen_hooks
    assert hearthsim_fragments in plugin.content.prompt_fragments


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_hearthsim"]), actor)
    assert applied[0].id == f"bunnyland_hearthsim.{PLUGIN_ID}"
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"cook", "eat-meal"} <= command_types
