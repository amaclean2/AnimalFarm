from __future__ import annotations

from typing import TYPE_CHECKING

from pos import Pos

if TYPE_CHECKING:
    from agents.agent import Agent
    from agents.scoring import ScoringContext


TASK_TO_NEED: dict[str, str] = {
    "seek_food": "hunger",
    "harvest_food": "hunger",
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

    thirst_urgency = (1.0 - agent.needs.water) ** 2

    if (
        closest_water_resource_dist is not None
        and closest_water_resource_dist + 2 >= agent.needs.get_ticks_to_empty("water")
    ):
        thirst_urgency = 1.0

    rest_urgency = (1.0 - agent.needs.rest) ** 2
    max_dist_to_rest = agent.needs.get_ticks_to_empty("rest")
    reachable_rest = agent.memory.query("rest", agent.pos, max_dist=max_dist_to_rest)

    if agent.memory.rest and reachable_rest is None:
        rest_urgency = 1.0

    return {
        "thirst": thirst_urgency,
        "hunger": (1.0 - agent.needs.hunger) ** 2,
        "rest": rest_urgency,
    }


def eligibility_threshold(
    agent: "Agent",
    candidate_task_name: str,
    urgencies: dict[str, float],
) -> float:
    idle_threshold = agent.behavioral_genome["idle_threshold"]

    if candidate_task_name == agent.active_task.name or agent.active_task.name == "explore":
        return idle_threshold

    current_need = TASK_TO_NEED.get(agent.active_task.name, "")
    breakaway_margin = agent.behavioral_genome["breakaway_margin"]
    return urgencies.get(current_need, 0.0) + breakaway_margin


def resolve_water_target(agent: "Agent", context: "ScoringContext") -> Pos | None:
    target = agent.memory.query("water", agent.pos)

    if target and context.occupied_tiles and target in context.occupied_tiles:
        target = agent.memory.query("water", agent.pos, exclude={target})

    return target


def resolve_food_target(agent: "Agent", context: "ScoringContext") -> Pos | None:
    return agent.memory.query("food", agent.pos, exclude=context.occupied_tiles)


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
