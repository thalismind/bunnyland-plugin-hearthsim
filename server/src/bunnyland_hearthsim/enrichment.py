"""World-generation enrichment: tag generated kitchens and food.

Generated objects expose semantic ``tags``/``wants``/``needs`` and an intent ``description``.
This hook scans that text and attaches cooking-pack markers — a stove for a generated oven or
kitchen range, and tagged ingredients for generated produce, meat, and staples — so cooking
works in generated worlds without the core generator knowing this plugin exists.
"""

from __future__ import annotations

import re

from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import GeneratedEntityEvent, ObjectGeneratedEvent
from bunnyland.core.world_actor import WorldActor

from .components import IngredientComponent, StoveComponent

#: Words that mark a generated object as a stove/appliance to cook at.
STOVE_TERMS = (
    "stove",
    "oven",
    "range",
    "cooktop",
    "hob",
    "grill",
    "hearth",
    "campfire",
    "kitchen",
)

#: ingredient tag -> words in generated text that imply it.
INGREDIENT_TAG_TERMS: dict[str, tuple[str, ...]] = {
    "vegetable": ("vegetable", "carrot", "potato", "onion", "cabbage", "turnip", "leek"),
    "fruit": ("fruit", "apple", "berry", "pear", "plum", "peach"),
    "meat": ("meat", "beef", "pork", "venison", "sausage", "poultry", "chicken"),
    "fish": ("fish", "trout", "salmon", "cod", "herring"),
    "grain": ("grain", "wheat", "flour", "bread", "oat", "rice", "barley"),
    "egg": ("egg", "eggs"),
    "dairy": ("dairy", "milk", "cheese", "butter", "cream"),
    "broth": ("broth", "stock", "bone"),
    "sweet": ("sweet", "sugar", "honey", "syrup"),
}


def _words(event: GeneratedEntityEvent) -> set[str]:
    """Whole-word tokens from a generated entity's semantic text.

    Word-level matching avoids substring false positives (e.g. "range" inside "orange").
    """
    generation = event.generation
    text = " ".join(
        (
            event.entity_kind,
            generation.description,
            *generation.tags,
            *generation.wants,
            *generation.needs,
        )
    ).casefold()
    return set(re.findall(r"[a-z]+", text))


def _ingredient_tags(words: set[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            tag
            for tag, terms in INGREDIENT_TAG_TERMS.items()
            if any(term in words for term in terms)
        )
    )


class HearthWorldgenHook:
    """Attach stove and ingredient markers to generated objects."""

    def subscribe(self, actor: WorldActor) -> None:
        self._actor = actor
        actor.bus.subscribe(ObjectGeneratedEvent, self._on_object)

    def _entity(self, entity_id: str):
        parsed = parse_entity_id(entity_id)
        if parsed is None or not self._actor.world.has_entity(parsed):
            return None
        return self._actor.world.get_entity(parsed)

    def _on_object(self, event: ObjectGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None:
            return
        words = _words(event)
        if not entity.has_component(StoveComponent) and any(term in words for term in STOVE_TERMS):
            replace_component(entity, StoveComponent())
            return
        if not entity.has_component(IngredientComponent):
            tags = _ingredient_tags(words)
            if tags:
                replace_component(entity, IngredientComponent(tags=tags))


__all__ = ["INGREDIENT_TAG_TERMS", "STOVE_TERMS", "HearthWorldgenHook"]
