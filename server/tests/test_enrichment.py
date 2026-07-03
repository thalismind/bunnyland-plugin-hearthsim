from __future__ import annotations

import asyncio

from bunnyland.core import IdentityComponent, WorldActor, spawn_entity
from bunnyland.core.components import GenerationIntentComponent
from bunnyland.core.events import ObjectGeneratedEvent, event_base
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_hearthsim import IngredientComponent, StoveComponent


def _actor():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_hearthsim"]), actor)
    return actor


def _generate_object(actor, *, name, tags=(), description=""):
    entity = spawn_entity(actor.world, [IdentityComponent(name=name, kind="item")])
    event = ObjectGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key=name,
        entity_kind="object",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        object_key=name,
    )
    asyncio.run(actor.bus.publish(event))
    return entity


def test_generated_oven_becomes_a_stove():
    actor = _actor()
    entity = _generate_object(actor, name="oven", tags=("kitchen", "appliance"))
    assert entity.has_component(StoveComponent)


def test_generated_produce_gets_ingredient_tags():
    actor = _actor()
    entity = _generate_object(actor, name="carrot", description="a fresh orange vegetable")
    assert entity.has_component(IngredientComponent)
    assert "vegetable" in entity.get_component(IngredientComponent).tags


def test_generated_meat_and_broth_bone_is_multi_tagged():
    actor = _actor()
    entity = _generate_object(actor, name="soup bone", tags=("meat", "bone"))
    assert entity.has_component(IngredientComponent)
    assert set(entity.get_component(IngredientComponent).tags) == {"broth", "meat"}


def test_plain_object_is_not_marked():
    actor = _actor()
    entity = _generate_object(actor, name="lamp", tags=("furniture", "brass"))
    assert not entity.has_component(StoveComponent)
    assert not entity.has_component(IngredientComponent)
