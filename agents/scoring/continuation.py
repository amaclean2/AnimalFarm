from __future__ import annotations

from typing import TYPE_CHECKING

from agents.scoring import ScoredCandidate, ScoringContext, register_scorer, scale_urgency
from agents.scoring.urgency import (
    TASK_TO_NEED,
    compute_urgencies,
    resolve_explore_goal,
    resolve_food_target,
    resolve_rest_target,
    resolve_thirst_explore_goal,
    resolve_water_target,
)


@register_scorer
def score_continue_search(agent: "Agent", context: ScoringContext) -> ScoredCandidate | None:

    active_task_name = agent.active_task.name

    if not active_task_name or active_task_name == "explore":
        return None

    if agent.needs.is_busy:
        return None

    need_name = TASK_TO_NEED.get(active_task_name, "")
    urgencies = compute_urgencies(agent)
    need_urgency = urgencies.get(need_name, 0.0)
    idle_threshold = agent.behavioral_genome["idle_threshold"]

    if need_urgency < idle_threshold:
        return None

    task_targets = {
        "seek_food": resolve_food_target(agent, context),
        "seek_water": resolve_water_target(agent, context),
        "seek_rest": resolve_rest_target(agent),
        "harvest_food": context.local_plant,
    }

    if active_task_name in task_targets and task_targets[active_task_name] is None:
        return None

    goal_by_task = {
        "seek_food": task_targets.get("seek_food"),
        "seek_water": task_targets.get("seek_water"),
        "thirst_explore": resolve_thirst_explore_goal(agent),
        "seek_rest": task_targets.get("seek_rest"),
    }
    goal = goal_by_task.get(active_task_name) or resolve_explore_goal(agent)

    return ScoredCandidate(active_task_name, scale_urgency(need_urgency), goal)
