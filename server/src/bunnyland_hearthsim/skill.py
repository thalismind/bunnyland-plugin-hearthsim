"""Cooking skill and mastery (mechanic 7).

Every successful cook grows a character's :class:`CookingSkillComponent`: one experience
point per dish, plus a little more for richer recipes. Experience crosses fixed thresholds
into named mastery tiers (novice -> home cook -> chef -> master chef). Mastery is not an
invisible stat tweak — it has two concrete effects:

- **quality**: a higher tier lengthens the buff a cooked meal grants (see
  :func:`meal_quality`), so a master chef's food comforts longer.
- **catering capacity**: a higher tier lets a caterer serve a larger table (see
  :func:`catering_capacity`), which is what the headline ``cater`` verb reads.

Everything here is a pure function of accumulated experience, so it stays deterministic.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity

#: (minimum experience, tier index, tier name), richest first for a simple scan.
_TIERS: tuple[tuple[float, int, str], ...] = (
    (60.0, 4, "master chef"),
    (30.0, 3, "chef"),
    (10.0, 2, "home cook"),
    (0.0, 1, "novice"),
)

#: Base experience for cooking any dish, plus a bonus scaled by how filling it is.
XP_PER_DISH = 1.0
XP_PER_SATIETY = 0.1

#: Diners a novice can cater to; each mastery tier above novice adds this many seats.
BASE_CATERING_SEATS = 2
SEATS_PER_TIER = 2

#: Buff-duration bonus per mastery tier above novice (10% longer per tier).
QUALITY_PER_TIER = 0.1


@dataclass(frozen=True)
class CookingSkillComponent(Component):
    """A character's cooking experience and the meals they have cooked."""

    experience: float = 0.0
    meals_cooked: int = 0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person or self.meals_cooked <= 0:
            return ()
        return (f"You are a {skill_tier_name(self.experience)} in the kitchen.",)


class CookingSkillImprovedEvent(DomainEvent):
    """A character's cooking crossed into a new mastery tier."""

    tier: str
    experience: float


def skill_tier(experience: float) -> int:
    """The mastery tier index (1..4) for an amount of cooking experience."""
    for threshold, index, _name in _TIERS:
        if experience >= threshold:
            return index
    return 1


def skill_tier_name(experience: float) -> str:
    """The mastery tier name for an amount of cooking experience."""
    for threshold, _index, name in _TIERS:
        if experience >= threshold:
            return name
    return "novice"


def meal_quality(experience: float) -> float:
    """Buff-duration multiplier a cook of this experience grants their meals (>= 1.0)."""
    return 1.0 + QUALITY_PER_TIER * (skill_tier(experience) - 1)


def catering_capacity(experience: float) -> int:
    """How many diners a caterer of this experience can serve at one spread."""
    return BASE_CATERING_SEATS + SEATS_PER_TIER * (skill_tier(experience) - 1)


def cooking_skill_of(character: Entity) -> CookingSkillComponent:
    """The character's skill component, or a fresh zero one if they've never cooked."""
    if character.has_component(CookingSkillComponent):
        return character.get_component(CookingSkillComponent)
    return CookingSkillComponent()


def dish_experience(satiety: float) -> float:
    """Experience earned for cooking a dish of the given satiety."""
    return XP_PER_DISH + XP_PER_SATIETY * satiety


def grant_cooking_experience(
    character: Entity, amount: float
) -> tuple[CookingSkillComponent, bool]:
    """Add experience (and one cooked dish) to a character's skill.

    Returns the updated component and whether the character crossed into a new tier.
    """
    current = cooking_skill_of(character)
    updated = replace(
        current,
        experience=current.experience + amount,
        meals_cooked=current.meals_cooked + 1,
    )
    replace_component(character, updated)
    return updated, skill_tier(updated.experience) > skill_tier(current.experience)


def cooking_skill_fragments(world, character: Entity) -> list[str]:
    """Foundation-prompt line for the character's own cooking mastery."""
    if not character.has_component(CookingSkillComponent):
        return []
    ctx = ComponentPromptContext.for_entity(world, character)
    return sorted(character.get_component(CookingSkillComponent).prompt_fragments(ctx))


__all__ = [
    "BASE_CATERING_SEATS",
    "QUALITY_PER_TIER",
    "SEATS_PER_TIER",
    "XP_PER_DISH",
    "XP_PER_SATIETY",
    "CookingSkillComponent",
    "CookingSkillImprovedEvent",
    "catering_capacity",
    "cooking_skill_fragments",
    "cooking_skill_of",
    "dish_experience",
    "grant_cooking_experience",
    "meal_quality",
    "skill_tier",
    "skill_tier_name",
]
