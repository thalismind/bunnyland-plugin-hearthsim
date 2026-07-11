"""Declarative stove and ingredient generation enrichment."""

import re

from bunnyland.core.generation import GenerationDelta, GenerationRequest

from .components import IngredientComponent, StoveComponent

STOVE_TERMS = ("stove", "oven", "range", "cooktop", "hob", "grill", "hearth", "campfire", "kitchen")
INGREDIENT_TAG_TERMS = {
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


def _words(request):
    text = " ".join(
        (request.source_key, request.entity_kind, request.description, *request.tags)
    ).casefold()
    return set(re.findall(r"[a-z]+", text))


class HearthGenerationEnricher:
    capabilities: tuple[str, ...] = ()

    def enrich(self, request: GenerationRequest) -> GenerationDelta:
        if request.entity_kind in {"room", "character"}:
            return GenerationDelta()
        existing = tuple(request.context.get("base_components", ()))
        words = _words(request)
        if not any(isinstance(item, StoveComponent) for item in existing) and any(
            term in words for term in STOVE_TERMS
        ):
            return GenerationDelta(components=(StoveComponent(),))
        if any(isinstance(item, IngredientComponent) for item in existing):
            return GenerationDelta()
        tags = tuple(
            sorted(
                tag
                for tag, terms in INGREDIENT_TAG_TERMS.items()
                if any(term in words for term in terms)
            )
        )
        return GenerationDelta(components=(IngredientComponent(tags=tags),) if tags else ())


__all__ = ["HearthGenerationEnricher", "INGREDIENT_TAG_TERMS", "STOVE_TERMS"]
