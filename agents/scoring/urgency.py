from __future__ import annotations

from typing import TYPE_CHECKING

from pos import Pos

from agents.scoring import TIER_BUSY

if TYPE_CHECKING:
    from agents.agent import Agent
    from agents.scoring import ScoringContext


TASK_TO_NEED: dict[str, str] = {
    "seek_food": "food",
    "harvest_food": "food",
    "eat": "hunger",
    "seek_water": "thirst",
    "drink": "thirst",
    "thirst_explore": "thirst",
    "sleep": "rest",
    "seek_rest": "rest",
}


def compute_urgencies(agent: "Agent") -> dict[str, float]:
    water_resources = agent.memory.water
    closest_water_resource_dist = (
        min(
            abs(resource.x - agent.x) + abs(resource.y - agent.y)
            for resource in water_resources
        )
        if water_resources
        else None
    )

    hunger_urgency = agent.needs.hunger ** 3
    food_urgency = (1.0 - agent.inventory.fullness) ** 3
    thirst_urgency = agent.needs.water ** 3
    rest_urgency = agent.needs.rest ** 3

    if (
        closest_water_resource_dist is not None
        and closest_water_resource_dist + 2 >= agent.needs.get_ticks_to_empty("water")
    ):
        thirst_urgency = TIER_BUSY

    return {
        "thirst": thirst_urgency,
        "hunger": hunger_urgency,
        "food": food_urgency,
        "rest": rest_urgency,
    }


def resolve_water_target(agent: "Agent", context: "ScoringContext") -> Pos | None:
    target = agent.memory.query("water", agent.pos)

    if target and context.occupied_tiles and target in context.occupied_tiles:
        target = agent.memory.query("water", agent.pos, exclude={target})

    return target


def resolve_food_target(agent: "Agent", context: "ScoringContext") -> Pos | None:
    return agent.memory.pick_best_food(
        agent.pos, agent.harvest_skill, exclude=context.occupied_tiles
    )


def resolve_rest_target(agent: "Agent") -> Pos | None:
    max_dist = agent.needs.get_ticks_to_empty("rest")
    return agent.memory.query("rest", agent.pos, max_dist=max_dist)


def resolve_thirst_explore_goal(agent: "Agent") -> Pos:
    if agent.active_task.name != "thirst_explore" or agent.active_task.goal_pos == agent.pos:
        return agent.get_thirst_explore_goal()
    return agent.active_task.goal_pos


def resolve_explore_goal(agent: "Agent") -> Pos:
    if agent.active_task.name != "explore" or agent.active_task.goal_pos == agent.pos:
        return agent.get_explore_goal()
    return agent.active_task.goal_pos
