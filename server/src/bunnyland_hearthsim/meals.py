"""Eating meals, meal buffs, and buff expiry (mechanic 3).

The ``eat-meal`` verb reuses the base hunger path — it relieves ``HungerComponent`` through
the shared ``Meter`` and emits the core ``FoodEatenEvent``/``HungerChangedEvent`` so existing
listeners (mood thoughts, projections) react exactly as they do for ordinary food — and adds
what the cooking pack is about: a timed :class:`~bunnyland_hearthsim.components.BuffComponent`
and a shared feast. A spoiled meal still fills the belly a little but grants no buff.

Buffs expire deterministically: :class:`BuffExpiryConsequence` removes a buff once the world
epoch reaches its ``expires_at_epoch``.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.actions import ActionArgument, ActionDefinition
from bunnyland.core.commands import CommandCost, Lane, SubmittedCommand
from bunnyland.core.ecs import container_of, remove_from_container, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_reachable_entity,
)
from bunnyland.foundation.meters.mechanics import band, changed
from bunnyland.foundation.needs.mechanics import FoodEatenEvent, HungerChangedEvent, HungerComponent
from relics import World

from .components import BuffComponent, FreshnessComponent, MealComponent
from .feasts import FeastEnjoyedEvent, share_feast

#: A spoiled meal is unpleasant: it fills far less and grants no buff.
SPOILED_SATIETY_FACTOR = 0.4


class MealEatenEvent(DomainEvent):
    """A character ate a cooked meal."""

    meal_id: str
    recipe: str
    spoiled: bool = False


class BuffAppliedEvent(DomainEvent):
    """A meal granted a timed buff."""

    buff: str
    expires_at_epoch: int


class BuffExpiredEvent(DomainEvent):
    """A character's meal buff wore off."""

    buff: str


class EatMealHandler:
    """Eat a reachable meal: restore hunger, apply a buff, and share any feast."""

    command_type = "eat-meal"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        meal_id, meal, rejection = require_reachable_entity(
            ctx,
            character,
            command.payload.get("meal_id"),
            invalid_reason="invalid meal id",
            missing_reason="meal does not exist",
            unreachable_reason="the meal is not within reach",
        )
        if rejection is not None:
            return rejection
        if not meal.has_component(MealComponent):
            return rejected("that is not a meal")
        if not character.has_component(HungerComponent):
            return rejected("character cannot eat")

        meal_component = meal.get_component(MealComponent)
        spoiled = (
            meal.has_component(FreshnessComponent)
            and meal.get_component(FreshnessComponent).spoiled
        )
        satiety = meal_component.satiety * (SPOILED_SATIETY_FACTOR if spoiled else 1.0)

        hunger = character.get_component(HungerComponent)
        new_meter = changed(hunger.meter, -satiety)
        replace_component(character, replace(hunger, meter=new_meter, last_ate_epoch=ctx.epoch))

        room_id = container_of(character)
        room_str = str(room_id) if room_id is not None else None
        events: list[DomainEvent] = [
            FoodEatenEvent(
                **ctx.event_base(
                    actor_id=str(character_id),
                    room_id=room_str,
                    target_ids=(str(meal_id),),
                    item_id=str(meal_id),
                    satiety=satiety,
                )
            ),
            HungerChangedEvent(
                **ctx.event_base(
                    actor_id=str(character_id),
                    value=new_meter.value,
                    band=band(new_meter),
                )
            ),
            MealEatenEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=room_str,
                    target_ids=(str(meal_id),),
                    meal_id=str(meal_id),
                    recipe=meal_component.name,
                    spoiled=spoiled,
                )
            ),
        ]

        if not spoiled:
            expires_at = ctx.epoch + meal_component.buff_duration
            replace_component(
                character,
                BuffComponent(
                    name=meal_component.buff,
                    magnitude=meal_component.buff_magnitude,
                    started_at_epoch=ctx.epoch,
                    expires_at_epoch=expires_at,
                ),
            )
            events.append(
                BuffAppliedEvent(
                    **ctx.event_base(
                        actor_id=str(character_id),
                        buff=meal_component.buff,
                        expires_at_epoch=expires_at,
                    )
                )
            )

        diners = share_feast(ctx.world, character, ctx.epoch)
        if diners:
            events.append(
                FeastEnjoyedEvent(
                    **ctx.event_base(
                        visibility=EventVisibility.ROOM,
                        actor_id=str(character_id),
                        room_id=room_str,
                        target_ids=tuple(str(diner.id) for diner in diners),
                        eater_id=str(character_id),
                        diner_ids=tuple(str(diner.id) for diner in diners),
                    )
                )
            )

        remove_from_container(ctx.world, meal_id)
        ctx.world.remove(meal_id)
        return ok(*events)


class BuffExpiryConsequence:
    """Remove meal buffs once their ``expires_at_epoch`` is reached (mechanic 3)."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for entity in list(world.query().with_all([BuffComponent]).execute_entities()):
            buff = entity.get_component(BuffComponent)
            if epoch >= buff.expires_at_epoch:
                entity.remove_component(BuffComponent)
                events.append(
                    BuffExpiredEvent(**event_base(epoch, actor_id=str(entity.id), buff=buff.name))
                )
        return events


EAT_MEAL_DEF = ActionDefinition(
    command_type="eat-meal",
    title="Eat a meal",
    description=(
        "Eat a cooked meal within reach. It restores hunger and, if still fresh, grants a "
        "timed buff; eating with others in the room makes it a shared feast."
    ),
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "meal_id": ActionArgument(
            title="Meal",
            description="The cooked meal to eat.",
            kind="entity",
            required=True,
        ),
    },
)

MEAL_ACTION_DEFINITIONS = (EAT_MEAL_DEF,)
MEAL_ACTION_HANDLERS = (EatMealHandler,)


__all__ = [
    "SPOILED_SATIETY_FACTOR",
    "BuffAppliedEvent",
    "BuffExpiredEvent",
    "BuffExpiryConsequence",
    "EAT_MEAL_DEF",
    "EatMealHandler",
    "MEAL_ACTION_DEFINITIONS",
    "MEAL_ACTION_HANDLERS",
    "MealEatenEvent",
]
