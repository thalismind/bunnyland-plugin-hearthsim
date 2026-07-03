from __future__ import annotations

from bunnyland.core import RoomComponent, WorldActor, spawn_entity
from bunnyland.mechanics.consumables import FoodComponent

from bunnyland_hearthsim import FreshnessComponent, SpoilageConsequence, freshness_state, spawn_meal
from bunnyland_hearthsim.freshness import FRESH, SPOILED, STALE
from bunnyland_hearthsim.recipes import recipe_by_name


def _meal(actor, epoch=0):
    room = spawn_entity(actor.world, [RoomComponent(title="Larder")])
    return spawn_meal(actor.world, recipe_by_name("garden salad"), epoch=epoch, room_id=room.id)


def test_freshness_state_bands():
    component = FreshnessComponent(cooked_at_epoch=0, spoils_after=100)
    assert freshness_state(component, 0) == FRESH
    assert freshness_state(component, 59) == FRESH
    assert freshness_state(component, 60) == STALE  # 60% of shelf life
    assert freshness_state(component, 100) == SPOILED
    assert freshness_state(FreshnessComponent(spoiled=True), 0) == SPOILED


def test_spoilage_marks_food_after_shelf_life():
    actor = WorldActor()
    meal = _meal(actor, epoch=0)
    spoils_after = meal.get_component(FreshnessComponent).spoils_after

    # Still fresh well before the shelf life expires.
    assert SpoilageConsequence().process(actor.world, spoils_after - 1) == []
    assert not meal.get_component(FreshnessComponent).spoiled

    events = SpoilageConsequence().process(actor.world, spoils_after)
    assert meal.get_component(FreshnessComponent).spoiled is True
    # The core food component is marked spoiled too, so the rest of the game agrees.
    assert meal.get_component(FoodComponent).spoiled is True
    assert [type(event).__name__ for event in events] == ["FoodSpoiledEvent"]
    assert events[0].item_id == str(meal.id)


def test_spoilage_is_idempotent():
    actor = WorldActor()
    meal = _meal(actor, epoch=0)
    spoils_after = meal.get_component(FreshnessComponent).spoils_after

    SpoilageConsequence().process(actor.world, spoils_after)
    # Already spoiled: a later pass emits nothing.
    assert SpoilageConsequence().process(actor.world, spoils_after + 1000) == []
