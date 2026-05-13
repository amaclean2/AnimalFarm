import random
from uuid import UUID

from mutations import inherit_or_mutate
from world import World

REPRODUCTION_CHANCE = 0.05
REPRODUCTION_HEALTH_THRESHOLD = 0.87
REPRODUCTION_RANGE = 3
REPRODUCTION_MATURITY_AGE = 30


def reproduce(world: World, events: list[tuple[str, dict]], tick_count: int) -> int:
    """Attempt reproduction for eligible pairs. Returns count of eligible pairs found."""
    agents = world.all_living_agents()
    paired: set[UUID] = set()
    eligible_pairs = 0

    for i, agent in enumerate(agents):
        if agent.id in paired or not agent.is_eligible_to_mate():
            continue
        for other in agents[i + 1:]:
            if other.id in paired or not other.is_eligible_to_mate():
                continue
            if abs(agent.x - other.x) + abs(agent.y - other.y) > REPRODUCTION_RANGE:
                continue
            eligible_pairs += 1
            if random.random() >= REPRODUCTION_CHANCE:
                continue

            spawn_candidates = [
                pos for pos in world.valid_moves(agent.x, agent.y)
                if not world.is_river_tile(*pos)
            ]
            if not spawn_candidates:
                continue

            sx, sy = random.choice(spawn_candidates)
            newborn = world.add_agent(sx, sy, birth_tick=tick_count)
            inherit_or_mutate(newborn, agent, other)
            events.append(("agent_born", {"agent": newborn.model_dump(mode="json")}))
            paired.add(agent.id)
            paired.add(other.id)
            break

    return eligible_pairs
