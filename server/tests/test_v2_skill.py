"""Behaviour tests for the v2 cooking-skill mechanic (mechanic 7)."""

from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective

from bunnyland_hearthsim.skill import (
    BASE_CATERING_SEATS,
    SEATS_PER_TIER,
    CookingSkillComponent,
    catering_capacity,
    cooking_skill_fragments,
    cooking_skill_of,
    dish_experience,
    grant_cooking_experience,
    meal_quality,
    skill_tier,
    skill_tier_name,
)


def _character(actor, *, skill=None, room=None):
    components = [IdentityComponent(name="Cook", kind="character"), CharacterComponent()]
    if skill is not None:
        components.append(skill)
    entity = spawn_entity(actor.world, components)
    if room is not None:
        room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), entity.id)
    return entity


def test_skill_tiers_climb_with_experience():
    assert (skill_tier(0.0), skill_tier_name(0.0)) == (1, "novice")
    assert (skill_tier(10.0), skill_tier_name(10.0)) == (2, "home cook")
    assert (skill_tier(30.0), skill_tier_name(30.0)) == (3, "chef")
    assert (skill_tier(60.0), skill_tier_name(60.0)) == (4, "master chef")


def test_negative_experience_stays_novice():
    # Defensive fallback: a sub-zero balance still reads as the lowest tier.
    assert skill_tier(-5.0) == 1
    assert skill_tier_name(-5.0) == "novice"


def test_quality_and_capacity_scale_with_tier():
    # Novice: base capacity, neutral quality.
    assert meal_quality(0.0) == 1.0
    assert catering_capacity(0.0) == BASE_CATERING_SEATS
    # Master chef: longer buffs and a bigger table.
    assert meal_quality(60.0) > 1.0
    assert catering_capacity(60.0) == BASE_CATERING_SEATS + SEATS_PER_TIER * 3


def test_dish_experience_scales_with_satiety():
    assert dish_experience(0.0) == 1.0
    assert dish_experience(30.0) > dish_experience(10.0)


def test_cooking_skill_of_defaults_to_zero():
    actor = WorldActor()
    fresh = _character(actor)
    skill = cooking_skill_of(fresh)
    assert skill.experience == 0.0 and skill.meals_cooked == 0


def test_grant_experience_accumulates_and_reports_level_up():
    actor = WorldActor()
    cook = _character(actor, skill=CookingSkillComponent(experience=8.0, meals_cooked=3))

    updated, leveled = grant_cooking_experience(cook, 5.0)  # 8 -> 13 crosses into home cook

    assert leveled is True
    assert updated.meals_cooked == 4
    assert updated.experience == 13.0
    # A further small gain stays within the tier -> no level-up.
    _again, leveled_again = grant_cooking_experience(cook, 1.0)
    assert leveled_again is False


def test_first_person_fragment_names_the_tier():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Kitchen")])
    cook = _character(
        actor, skill=CookingSkillComponent(experience=30.0, meals_cooked=12), room=room
    )
    lines = cooking_skill_fragments(actor.world, cook)
    assert lines == ["You are a chef in the kitchen."]


def test_third_person_and_uncooked_yield_no_fragment():
    actor = WorldActor()
    other = _character(actor)
    cooked = _character(actor, skill=CookingSkillComponent(experience=30.0, meals_cooked=12))
    third = ComponentPromptContext.for_entity(
        actor.world, cooked, perspective=PromptPerspective(viewer=other)
    )
    assert cooked.get_component(CookingSkillComponent).prompt_fragments(third) == ()
    # A character who has never cooked, even in first person, says nothing.
    never = CookingSkillComponent(experience=0.0, meals_cooked=0)
    first = ComponentPromptContext.for_entity(actor.world, cooked)
    assert never.prompt_fragments(first) == ()


def test_fragments_helper_empty_without_component():
    actor = WorldActor()
    plain = _character(actor)
    assert cooking_skill_fragments(actor.world, plain) == []
