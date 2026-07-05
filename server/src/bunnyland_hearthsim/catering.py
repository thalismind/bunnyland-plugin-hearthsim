"""Catering: the headline mechanic (mechanic 9).

Catering is cooking *for a room*. A caterer with a reachable stove or appliance and enough
ingredients lays on a spread and serves everyone present at once. It routes straight through
core systems rather than reinventing any of them:

- **hunger** — each diner's core :class:`~bunnyland.mechanics.needs.HungerComponent` is
  relieved and a core ``FoodEatenEvent`` is emitted, so the shared affect reactor lifts every
  diner's mood exactly as it does for an ordinary meal.
- **social** — the caterer's :class:`~bunnyland.mechanics.social.SocialBond` to each diner
  (and back) warms; a full belly among friends builds affinity, familiarity, and trust.
- **catering relationship** — a repeatable, structural bond is its own typed
  :class:`CateredFor` edge (one index), tallying how often and how much the caterer has fed
  each diner — never a list crammed onto a component.
- **storyteller** — catering a room answers a pending communal-feast incident.

How large a table a caterer can serve scales with their cooking mastery
(:func:`~bunnyland_hearthsim.skill.catering_capacity`).
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import Contains
from bunnyland.core.actions import ActionDefinition
from bunnyland.core.commands import CommandCost, Lane, SubmittedCommand
from bunnyland.core.ecs import container_of, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
)
from bunnyland.mechanics.meter import band, changed
from bunnyland.mechanics.needs import (
    FoodEatenEvent,
    HungerChangedEvent,
    HungerComponent,
    SocialNeedComponent,
    recover_daily_need,
)
from bunnyland.mechanics.social import adjust_bond
from pydantic.dataclasses import dataclass
from relics import Edge, World

from .appliances import unlocked_appliance_recipes, unlocked_categories
from .cooking import _inventory_ingredients, _reachable_stove
from .feasts import diners_in_room
from .recipes import find_recipe
from .skill import (
    CookingSkillImprovedEvent,
    catering_capacity,
    cooking_skill_of,
    dish_experience,
    grant_cooking_experience,
    skill_tier_name,
)
from .storyteller import resolve_feast_incident

#: How catering warms the caterer<->diner bond, and relieves each diner's loneliness.
CATER_AFFINITY = 0.08
CATER_FAMILIARITY = 0.05
CATER_TRUST = 0.03
CATER_SOCIAL_RECOVERY = 12.0


@dataclass(frozen=True)
class CateredFor(Edge):
    """caterer -> diner. A repeatable "I have fed you" relationship, tallied over time."""

    times: int = 0
    total_dishes: int = 0
    last_epoch: int = 0


class MealCateredEvent(DomainEvent):
    """A caterer served a spread to a room."""

    caterer_id: str
    recipe: str
    diner_ids: tuple[str, ...]


def catering_bond(world: World, caterer_id, diner_id) -> CateredFor | None:
    """The caterer->diner catering edge, or ``None`` if they've never been catered to."""
    for edge, target in world.get_entity(caterer_id).get_relationships(CateredFor):
        if target == diner_id:
            return edge
    return None


def record_catering(world: World, caterer_id, diner_id, *, dishes: int, epoch: int) -> CateredFor:
    """Strengthen (or open) the caterer->diner :class:`CateredFor` edge."""
    current = catering_bond(world, caterer_id, diner_id) or CateredFor()
    updated = CateredFor(
        times=current.times + 1,
        total_dishes=current.total_dishes + dishes,
        last_epoch=epoch,
    )
    world.get_entity(caterer_id).add_relationship(updated, diner_id)
    return updated


class CaterHandler:
    """Cater a spread to everyone in the room: feed them, warm bonds, answer the feast call."""

    command_type = "cater"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        if _reachable_stove(ctx, character) is None:
            return rejected("no stove is within reach")
        ingredients = _inventory_ingredients(ctx.world, character)
        if not ingredients:
            return rejected("you have no ingredients to cater with")
        diners = diners_in_room(ctx.world, character)
        if not diners:
            return rejected("no one here to cater for")

        categories = unlocked_categories(ctx.world, character)
        extra = unlocked_appliance_recipes(categories)
        match = find_recipe(ingredients, extra=extra)
        if match is None:
            return rejected("no recipe matches your ingredients")
        recipe, used_ids = match

        capacity = catering_capacity(cooking_skill_of(character).experience)
        served = diners[:capacity]
        for ingredient_id in used_ids:
            character.remove_relationship(Contains, ingredient_id)
            ctx.world.remove(ingredient_id)

        room_id = container_of(character)
        room_str = str(room_id) if room_id is not None else None
        warmth = {
            "affinity": CATER_AFFINITY,
            "familiarity": CATER_FAMILIARITY,
            "trust": CATER_TRUST,
        }
        events: list[DomainEvent] = []
        for diner in served:
            self._feed(ctx, diner, recipe.satiety, room_str, events)
            adjust_bond(ctx.world, character_id, diner.id, warmth)
            adjust_bond(ctx.world, diner.id, character_id, warmth)
            if diner.has_component(SocialNeedComponent):
                recover_daily_need(
                    diner,
                    SocialNeedComponent,
                    CATER_SOCIAL_RECOVERY,
                    ctx.epoch,
                    timestamp_field="last_social_epoch",
                )
            record_catering(ctx.world, character_id, diner.id, dishes=1, epoch=ctx.epoch)

        skill, leveled_up = grant_cooking_experience(
            character, dish_experience(recipe.satiety)
        )
        events.append(
            MealCateredEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=room_str,
                    target_ids=tuple(str(diner.id) for diner in served),
                    caterer_id=str(character_id),
                    recipe=recipe.name,
                    diner_ids=tuple(str(diner.id) for diner in served),
                )
            )
        )
        if leveled_up:
            events.append(
                CookingSkillImprovedEvent(
                    **ctx.event_base(
                        actor_id=str(character_id),
                        tier=skill_tier_name(skill.experience),
                        experience=skill.experience,
                    )
                )
            )
        room = ctx.world.get_entity(room_id) if room_id is not None else None
        resolved = resolve_feast_incident(
            ctx.world, room, ctx.epoch, actor_id=str(character_id)
        )
        if resolved is not None:
            events.append(resolved)
        return ok(*events)

    def _feed(self, ctx, diner, satiety, room_str, events) -> None:
        """Relieve a diner's core hunger and emit the core food/hunger events."""
        if not diner.has_component(HungerComponent):
            return
        hunger = diner.get_component(HungerComponent)
        new_meter = changed(hunger.meter, -satiety)
        replace_component(diner, replace(hunger, meter=new_meter, last_ate_epoch=ctx.epoch))
        events.append(
            FoodEatenEvent(
                **ctx.event_base(
                    actor_id=str(diner.id),
                    room_id=room_str,
                    item_id="",
                    satiety=satiety,
                )
            )
        )
        events.append(
            HungerChangedEvent(
                **ctx.event_base(
                    actor_id=str(diner.id),
                    value=new_meter.value,
                    band=band(new_meter),
                )
            )
        )


CATER_DEF = ActionDefinition(
    command_type="cater",
    title="Cater a meal",
    description=(
        "Cook a spread at a stove within reach and serve everyone in the room at once. It "
        "fills their bellies, warms your bonds with them, and answers any call for a feast."
    ),
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={},
)

CATERING_ACTION_DEFINITIONS = (CATER_DEF,)
CATERING_ACTION_HANDLERS = (CaterHandler,)


__all__ = [
    "CATERING_ACTION_DEFINITIONS",
    "CATERING_ACTION_HANDLERS",
    "CATER_AFFINITY",
    "CATER_DEF",
    "CATER_FAMILIARITY",
    "CATER_SOCIAL_RECOVERY",
    "CATER_TRUST",
    "CaterHandler",
    "CateredFor",
    "MealCateredEvent",
    "catering_bond",
    "record_catering",
]
