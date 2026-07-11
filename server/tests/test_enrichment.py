import asyncio

from bunnyland.core import WorldActor
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import ObjectSpec, RoomSpec, WorldProposal, instantiate

from bunnyland_hearthsim import IngredientComponent, StoveComponent
from bunnyland_hearthsim.plugin import bunnyland_plugins as _plugins


def _object(name, *, description="", tags=()):
    actor = WorldActor()
    apply_plugins(_plugins(), actor)
    result = asyncio.run(
        instantiate(
            actor,
            WorldProposal(
                seed="seed",
                rooms=[RoomSpec(key="room", title="Room")],
                objects=[
                    ObjectSpec(
                        key="item", name=name, room_key="room", description=description, tags=tags
                    )
                ],
            ),
        )
    )
    return actor.world.get_entity(result.objects["item"])


def test_generated_oven_becomes_a_stove():
    assert _object("oven", tags=("kitchen",)).has_component(StoveComponent)


def test_generated_produce_gets_ingredient_tags():
    assert _object("carrot", description="a fresh orange vegetable").get_component(
        IngredientComponent
    ).tags == ("vegetable",)


def test_generated_meat_and_broth_bone_is_multi_tagged():
    assert _object("soup bone", tags=("meat", "bone")).get_component(IngredientComponent).tags == (
        "broth",
        "meat",
    )


def test_plain_object_is_ignored():
    item = _object("spoon")
    assert not item.has_component(StoveComponent)
    assert not item.has_component(IngredientComponent)
