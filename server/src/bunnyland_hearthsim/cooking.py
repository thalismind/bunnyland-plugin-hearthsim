"""The ``cook`` verb (mechanic 2).

Cooking requires a :class:`~bunnyland_hearthsim.components.StoveComponent` the character can
reach (held stoves are unusual but allowed; a stove in the room is the norm) and enough
tagged ingredients in the character's inventory to satisfy a recipe. On success it consumes
the matched ingredients and produces a cooked meal in the character's hands.

Validation order follows the project convention: invalid id -> missing entity -> wrong kind
/ unreachable -> missing-resource checks -> apply.
"""

from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    contents,
    reachable_ids,
)
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.ecs import container_of
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    planned,
    rejected,
    require_character,
    require_reachable_entity,
)
from bunnyland.core.mutations import (
    AddEdge,
    AddEntity,
    DeleteEntity,
    EntityReference,
    MutationPlan,
    SetComponent,
)
from bunnyland.foundation.consumables.components import ConsumableComponent, FoodComponent

from .appliances import (
    CATEGORY_APPLIANCE,
    unlocked_appliance_recipes,
    unlocked_categories,
)
from .components import FreshnessComponent, IngredientComponent, MealComponent, StoveComponent
from .recipes import (
    APPLIANCE_RECIPE_NAMES,
    RECIPE_NAMES,
    appliance_recipe_by_name,
    find_recipe,
)
from .skill import (
    CookingSkillImprovedEvent,
    advanced_cooking_skill,
    cooking_skill_of,
    dish_experience,
    meal_quality,
    skill_tier_name,
)


class MealCookedEvent(DomainEvent):
    """A character cooked a meal at a stove."""

    stove_id: str
    meal_id: str
    recipe: str


def _reachable_stove(ctx: HandlerContext, character):
    """Return the lowest-id reachable stove, or ``None`` if none is within reach."""
    stoves = [
        ctx.world.get_entity(entity_id)
        for entity_id in reachable_ids(ctx.world, character)
        if ctx.world.get_entity(entity_id).has_component(StoveComponent)
    ]
    if not stoves:
        return None
    return sorted(stoves, key=lambda entity: str(entity.id))[0]


def _inventory_ingredients(world, character) -> list[tuple[object, frozenset[str]]]:
    """Return ``(id, tags)`` for each ingredient in the character's inventory, id-sorted."""
    gathered: list[tuple[object, frozenset[str]]] = []
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if item.has_component(IngredientComponent):
            gathered.append((item_id, frozenset(item.get_component(IngredientComponent).tags)))
    return sorted(gathered, key=lambda pair: str(pair[0]))


class CookHandler:
    """Cook a meal at a reachable stove from ingredients in the character's inventory."""

    command_type = "cook"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection

        stove = self._resolve_stove(ctx, character, command)
        if isinstance(stove, HandlerResult):
            return stove

        ingredients = _inventory_ingredients(ctx.world, character)
        if not ingredients:
            return rejected("you have no ingredients to cook with")

        categories = unlocked_categories(ctx.world, character)
        requested = command.payload.get("recipe")
        rejection = self._validate_recipe_name(requested, categories)
        if rejection is not None:
            return rejection

        extra = unlocked_appliance_recipes(categories)
        match = find_recipe(ingredients, name=requested, extra=extra)
        if match is None:
            if requested is not None:
                return rejected(f"you are missing ingredients for {requested}")
            return rejected("no recipe matches your ingredients")

        recipe, used_ids = match
        quality = meal_quality(cooking_skill_of(character).experience)
        skill, leveled_up = advanced_cooking_skill(character, dish_experience(recipe.satiety))
        meal_ref = EntityReference()
        meal_component = MealComponent(
            name=recipe.name,
            buff=recipe.buff,
            buff_magnitude=recipe.buff_magnitude,
            buff_duration=int(recipe.buff_duration * quality),
            satiety=recipe.satiety,
            nutrition=recipe.nutrition,
        )
        operations = [
            AddEntity(
                (
                    IdentityComponent(name=recipe.name, kind="item", tags=("hearthsim", "meal")),
                    PortableComponent(),
                    HoldableComponent(slot="hand"),
                    ConsumableComponent(current_uses=1, max_uses=1),
                    FoodComponent(nutrition=recipe.nutrition, satiety=recipe.satiety),
                    meal_component,
                    FreshnessComponent(cooked_at_epoch=ctx.epoch, spoils_after=recipe.spoils_after),
                ),
                reference=meal_ref,
            ),
            AddEdge(
                character_id,
                meal_ref,
                Contains(mode=ContainmentMode.INVENTORY),
            ),
            SetComponent(character_id, skill),
            *(DeleteEntity(ingredient_id) for ingredient_id in used_ids),
        ]

        room_id = container_of(character)
        room_str = str(room_id) if room_id is not None else None
        events = [
            lambda: MealCookedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=room_str,
                    target_ids=(str(stove.id), str(meal_ref.require())),
                    stove_id=str(stove.id),
                    meal_id=str(meal_ref.require()),
                    recipe=recipe.name,
                )
            )
        ]
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
        return planned(MutationPlan(tuple(operations)), *events)

    def _validate_recipe_name(self, requested, categories):
        """Reject an unknown or appliance-locked recipe name; ``None`` if it is cookable."""
        if requested is None or requested in RECIPE_NAMES:
            return None
        if requested in APPLIANCE_RECIPE_NAMES:
            recipe = appliance_recipe_by_name(requested)
            if recipe.category not in categories:
                appliance = CATEGORY_APPLIANCE[recipe.category]
                return rejected(f"you need a {appliance} to cook {requested}")
            return None
        return rejected("unknown recipe")

    def _resolve_stove(self, ctx: HandlerContext, character, command: SubmittedCommand):
        """Return the stove entity to cook at, or a rejection HandlerResult."""
        raw_stove = command.payload.get("stove_id")
        if raw_stove is None:
            stove = _reachable_stove(ctx, character)
            if stove is None:
                return rejected("no stove is within reach")
            return stove
        _stove_id, stove, rejection = require_reachable_entity(
            ctx,
            character,
            raw_stove,
            invalid_reason="invalid stove id",
            missing_reason="stove does not exist",
            unreachable_reason="the stove is not within reach",
        )
        if rejection is not None:
            return rejection
        if not stove.has_component(StoveComponent):
            return rejected("that is not a stove")
        return stove


COOK_DEF = ActionDefinition(
    command_type="cook",
    title="Cook a meal",
    description=(
        "Cook at a stove within reach, turning ingredients you are carrying into a meal. "
        "Optionally name a recipe or a specific stove."
    ),
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.EXTENDED),
    arguments={
        "stove_id": ActionArgument(
            title="Stove",
            description="The stove to cook at; omit to use any stove within reach.",
            kind="entity",
        ),
        "recipe": ActionArgument(
            title="Recipe",
            description="Name a specific recipe to make; omit to make the best you can.",
            kind="string",
        ),
    },
)

COOK_ACTION_DEFINITIONS = (COOK_DEF,)
COOK_ACTION_HANDLERS = (CookHandler,)


__all__ = [
    "COOK_ACTION_DEFINITIONS",
    "COOK_ACTION_HANDLERS",
    "COOK_DEF",
    "CookHandler",
    "MealCookedEvent",
]
