import random
from uuid import UUID

import config as _cfg
from agents import Agents
from agents.mutations import inherit_or_mutate
from config import (
    REPRODUCTION_HUNGER_THRESHOLD,
    REPRODUCTION_RANGE,
)
from world import World


def reproduce(
    world: World, agents: Agents, events: list[tuple[str, dict]], tick_count: int
) -> int:
    """Attempt reproduction for eligible pairs. Returns count of eligible pairs found."""
    all_agents = agents.all_living
    paired: set[UUID] = set()
    eligible_pairs = 0

    for i, agent in enumerate(all_agents):
        if agent.id in paired or not agent.is_eligible_to_mate(tick_count):
            continue
        for other in all_agents[i + 1 :]:
            if other.id in paired or not other.is_eligible_to_mate(tick_count):
                continue
            if abs(agent.x - other.x) + abs(agent.y - other.y) > REPRODUCTION_RANGE:
                continue
            eligible_pairs += 1
            if random.random() >= _cfg.REPRODUCTION_CHANCE:
                continue

            spawn_candidates = [
                pos
                for pos in world.valid_moves(agent.pos)
                if not world.rivers.is_river_tile(pos)
            ]
            if not spawn_candidates:
                continue

            spawn_pos = random.choice(spawn_candidates)
            newborn = agents.add(spawn_pos, birth_tick=tick_count)
            inherit_or_mutate(newborn, agent, other)
            events.append(("agent_born", {"agent": newborn.model_dump(mode="json")}))
            agent.last_mated_tick = tick_count
            other.last_mated_tick = tick_count
            paired.add(agent.id)
            paired.add(other.id)
            break

    return eligible_pairs
