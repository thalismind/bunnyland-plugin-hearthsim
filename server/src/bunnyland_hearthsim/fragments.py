"""Prompt fragment provider for the cooking pack.

A single ``(world, character) -> list[str]`` provider feeds both the LLM actor context and
the human character-chat prompt. It surfaces the pack's newly visible state deterministically:
the character's own meal buff, any stove they can reach, and the freshness of nearby meals.
Freshness is read from the food's own ``spoiled`` flag (maintained by the spoilage
consequence), so the provider needs no epoch and stays a pure function of world state.
"""

from __future__ import annotations

from bunnyland.core import reachable_ids
from bunnyland.core.ecs import entity_name
from relics import Entity, World

from .components import BuffComponent, FreshnessComponent, MealComponent, StoveComponent


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def hearthsim_fragments(world: World, character: Entity) -> list[str]:
    lines: list[str] = []
    if character.has_component(BuffComponent):
        buff = character.get_component(BuffComponent)
        lines.append(f"You feel {buff.name} after a good meal.")
    for entity_id in reachable_ids(world, character):
        entity = world.get_entity(entity_id)
        if entity.has_component(StoveComponent):
            name = entity_name(entity, "stove")
            lines.append(f"{_capitalize(name)} stands here, ready for cooking.")
        if entity.has_component(MealComponent):
            name = entity_name(entity, "a meal")
            spoiled = (
                entity.has_component(FreshnessComponent)
                and entity.get_component(FreshnessComponent).spoiled
            )
            if spoiled:
                lines.append(f"{_capitalize(name)} here has spoiled and smells foul.")
            else:
                lines.append(f"{_capitalize(name)} here looks fresh and appetizing.")
    return sorted(dict.fromkeys(lines))


__all__ = ["hearthsim_fragments"]
