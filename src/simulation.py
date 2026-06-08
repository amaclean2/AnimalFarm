import random
from dataclasses import dataclass
from uuid import uuid4

from agents import Agents
from agents.agent import Agent
from clock import DAY_LENGTH
from genome_pool import GenomePool
from plant import Plant, VegetationManager
from movement import best_move
from pos import Pos
from tasks import Task
from pathfinding import astar
import config as cfg
import event_bus
from events import Event
from world import World


@dataclass
class VisionSnapshot:
    food_targets: list[Plant]
    visible_water: list[Pos]
    visible_rest: Pos | None


class Simulation:
    def __init__(
        self,
        world: World,
        vegetation: VegetationManager,
        agents: Agents,
        genome_pool: GenomePool | None = None,
    ) -> None:
        self.world = world
        self.vegetation = vegetation
        self.agents = agents

        self._genome_pool = genome_pool
        self._sim_id: str = str(uuid4())[:8]
        self.tick_count: int = 0

    def reset(self) -> None:
        self._sim_id = str(uuid4())[:8]
        self.world.reset()
        self.vegetation.reset()
        self.agents.reset()

    def _plan_steps(
        self,
        agent: Agent,
        valid_moves: list[Pos],
        snapshot: VisionSnapshot,
        occupied_tiles: set[Pos] | None = None,
        rest_target: Pos | None = None,
    ) -> list[Pos]:
        vision = float(agent.vision_range)
        top_task = agent.choose_action(
            self.agents.find_mate_target(agent, vision, self.tick_count),
            agent.explore_goal(self.world.width, self.world.height, self.tick_count),
            agent.thirst_explore_goal(
                self.world.width, self.world.height, self.tick_count
            ),
            self.tick_count,
            visible_water=snapshot.visible_water,
            rest_target=rest_target,
        )

        if top_task.name == "seek_food" and top_task.goal_pos == agent.pos:
            return [agent.pos]

        if top_task.name == "seek_food" and snapshot.food_targets:
            nearest = min(
                snapshot.food_targets,
                key=lambda f: abs(f.x - agent.x) + abs(f.y - agent.y),
            )
            top_task = Task(
                priority=top_task.priority,
                name="seek_food",
                goal_pos=nearest.pos,
            )

        if top_task.name == "drink" and snapshot.visible_water:
            nearest_water = min(
                snapshot.visible_water,
                key=lambda pos: abs(pos.x - agent.x) + abs(pos.y - agent.y),
            )
            top_task = Task(
                priority=top_task.priority,
                name="drink",
                goal_pos=nearest_water,
            )

        if agent.needs_replan(top_task):
            radius = (
                None if top_task.name in ("explore", "thirst_explore") else int(vision)
            )
            agent.path = astar(
                self.world, agent.pos, top_task.goal_pos, occupied_tiles, radius
            )
            agent.active_task = top_task

        first_step = None
        
        if agent.path:
            step = agent.path[0]
            if step in valid_moves:
                agent.path.pop(0)
                first_step = step
            else:
                agent.path = astar(
                    self.world,
                    agent.pos,
                    top_task.goal_pos,
                    occupied_tiles,
                    int(vision),
                )
                
                if agent.path and agent.path[0] in valid_moves:
                    first_step = agent.path.pop(0)
                elif (agent.id.int + self.tick_count) % 2 == 0:
                    first_step = agent.pos
        elif top_task.name == "sleep":
            first_step = agent.pos
            
        pathfinding_food_targets = (
            []
            if top_task.name in ("thirst_explore", "seek_water")
            else snapshot.food_targets
        )

        if first_step is None:
            first_step = best_move(agent, valid_moves, pathfinding_food_targets)

        steps = [first_step]

        if first_step != agent.pos and agent.path:
            steps.append(agent.path[0])

        return steps

    def _harvest_tick(self, agent: Agent) -> bool:
        if agent.harvest_count == 0:
            return False

        local_plant = self.vegetation.get_plant_at(agent.pos)
        if local_plant is None:
            agent.harvest_count = 0
            return False

        agent.harvest_count -= 1
        if agent.harvest_count > 0:
            return False

        local_plant.remove(1)
        agent.eat()
        
        event_bus.publish(
            Event(
                "fruit_harvested",
                {
                    "agent_id": str(agent.id),
                    "plant_id": str(local_plant.id),
                    "fruit_count_remaining": local_plant.fruit_count,
                    "yield": 1,
                },
            )
        )
        event_bus.publish(
            Event(
                "agent_ate",
                {
                    "agent": agent.model_dump(mode="json"),
                    "plant_id": str(local_plant.id),
                },
            )
        )
        
        if local_plant.fruit_count < 1:
            event_bus.publish(
                Event(
                    "fruit_depleted",
                    {
                        "plant_id": str(local_plant.id),
                        "x": local_plant.x,
                        "y": local_plant.y,
                    },
                )
            )
        return True

    def _build_vision_snapshot(
        self,
        agent: Agent,
        sleeping_tiles: set[Pos],
    ) -> VisionSnapshot:
        vision = float(agent.vision_range)

        food_targets = self.vegetation.visible_for(agent.id)
        if (
            agent.active_task is not None
            and agent.active_task.name == "seek_food"
            and agent.path
        ):
            close_plants = self.vegetation.nearby_in_vision(agent.id, agent.pos, 5)
            if close_plants:
                food_targets = close_plants

        if agent.needs.water < 0.9:
            visible_water = self.world.rivers.tiles_near(agent.pos, int(vision))
        else:
            visible_water = []

        if agent.needs.rest < 0.8:
            visible_rest = self.world.suitable_rest_in_vision(agent, 10, sleeping_tiles)
        else:
            visible_rest = None

        return VisionSnapshot(
            food_targets=food_targets,
            visible_water=visible_water,
            visible_rest=visible_rest,
        )

    def _decide_agent_step(
        self,
        agent: Agent,
        occupied_tiles: set[Pos],
        sleeping_tiles: set[Pos],
        is_night: bool,
    ) -> bool:
        moves = self.world.valid_moves(agent.pos)
        if not moves:
            return False

        valid_moves = [m for m in moves if m not in occupied_tiles]
        if not valid_moves:
            return False

        shade = self.vegetation.shade_at(agent.pos)
        temperature = cfg.temp_to_c(
            max(0.0, self.world.weather.temperature_grid[agent.get_pos_idx()] - shade)
        )
        agent.increment_needs(
            is_night,
            tile_quality=self.world.rest_quality_at(agent.pos),
            temperature=temperature,
        )

        snapshot = self._build_vision_snapshot(agent, sleeping_tiles)

        agent.update_food_memory(snapshot.food_targets, self.tick_count)
        agent.update_water_memory(snapshot.visible_water, self.tick_count)
        agent.update_rest_target(snapshot.visible_rest, sleeping_tiles)

        at_rest_target = agent.rest_target is None or agent.pos == agent.rest_target
        was_sleeping = agent.is_sleeping
        agent.tick_sleep()

        agent.sleep_if_ready(at_rest_target, self.world.rivers.is_river_tile(agent.pos))

        if was_sleeping and not agent.is_sleeping:
            agent.rest_target = None

        old_pos = agent.pos
        if agent.is_sleeping or agent.harvest_count > 0:
            agent.planned_steps.clear()
            agent.next_decision_tick = self.tick_count + 1
        else:
            plant_at_pos = None
            if agent.active_task is not None and agent.active_task.name == "seek_food":
                plant_at_pos = self.vegetation.fruiting_plant_at(agent.pos)

            if plant_at_pos is not None:
                agent.begin_harvest(plant_at_pos)
                if agent.harvest_count > 0:
                    event_bus.publish(
                        Event(
                            "harvest_started",
                            {
                                "agent_id": str(agent.id),
                                "plant_id": str(plant_at_pos.id),
                            },
                        )
                    )
                agent.planned_steps.clear()
                agent.next_decision_tick = self.tick_count + 1
            else:
                planned = self._plan_steps(
                    agent,
                    valid_moves,
                    snapshot,
                    occupied_tiles,
                    rest_target=agent.rest_target,
                )
                agent.move_to(planned[0])
                agent.planned_steps = planned[1:]
                agent.next_decision_tick = self.tick_count + len(planned)

        occupied_tiles.discard(old_pos)
        occupied_tiles.add(agent.pos)
        agent.age += 1

        if agent.pos != old_pos and not agent.is_sleeping:
            elev_gain = self.world.elevation_at(agent.pos) - self.world.elevation_at(
                old_pos
            )
            if elev_gain > 0:
                agent.drain_uphill(elev_gain)

        ate_this_tick = self._harvest_tick(agent)

        if self.world.rivers.is_river_tile(agent.pos):
            agent.drink()
            event_bus.publish(Event("agent_drank", {"agent_id": str(agent.id)}))

        if not ate_this_tick and not agent.is_sleeping:
            agent.apply_hunger_drain(self.world.rivers.is_river_tile(agent.pos))

        event_bus.publish(
            Event("agent_moved", {"agent": agent.model_dump(mode="json")})
        )

    def _execute_agent_step(
        self,
        agent: Agent,
        occupied_tiles: set[Pos],
        is_night: bool,
    ) -> bool:
        tile_quality = self.world.rest_quality_at(agent.pos)
        shade = self.vegetation.shade_at(agent.pos)
        temperature = cfg.temp_to_c(
            max(
                0.0,
                self.world.weather.temperature_grid[agent.get_pos_idx()] - shade,
            )
        )
        agent.increment_needs(
            is_night, tile_quality=tile_quality, temperature=temperature
        )

        old_pos = agent.pos

        agent.tick_movement(
            self.world.rivers.is_river_tile,
            occupied_tiles,
            self.tick_count,
            tile_quality,
        )

        if agent.pos != old_pos:
            elev_gain = self.world.elevation_at(agent.pos) - self.world.elevation_at(
                old_pos
            )
            if elev_gain > 0:
                agent.drain_uphill(elev_gain)

        ate_this_tick = self._do_harvest_tick(agent)

        if self.world.rivers.is_river_tile(agent.pos):
            agent.drink()
            event_bus.publish(Event("agent_drank", {"agent_id": str(agent.id)}))

        if not ate_this_tick and not agent.is_sleeping:
            agent.apply_hunger_drain(self.world.rivers.is_river_tile(agent.pos))

        event_bus.publish(
            Event("agent_moved", {"agent": agent.model_dump(mode="json")})
        )

    def _process_agents(
        self,
        all_living: list,
        occupied_tiles: set,
        sleeping_tiles: set,
        is_night: bool,
    ) -> None:
        deciding_agents = [
            a for a in all_living if self.tick_count >= a.next_decision_tick
        ]
        executing_agents = [
            a for a in all_living if self.tick_count < a.next_decision_tick
        ]

        dead = []

        for agent in executing_agents:
            self._execute_agent_step(agent, occupied_tiles, is_night)

            if agent.should_die():
                dead.append(agent.id)

        for agent in deciding_agents:
            self._decide_agent_step(
                agent,
                occupied_tiles,
                sleeping_tiles,
                is_night,
            )

            if agent.should_die():
                dead.append(agent.id)

        for agent_id in dead:
            if self._genome_pool is not None:
                agent = self.agents.get(agent_id)

                if agent:
                    self._genome_pool.record(agent, self._sim_id, self.tick_count)

            self.agents.process_agent_death(agent_id)

        self.agents.reproduce(self.world, self.tick_count)

    def on_tick(self, tick_count: int) -> list[Event]:
        self.tick_count = tick_count
        is_night = (tick_count % DAY_LENGTH) >= DAY_LENGTH // 2
        self.world.weather.set_day_phase((tick_count % DAY_LENGTH) / DAY_LENGTH)

        self.vegetation.grow_plants(tick_count)

        all_living = self.agents.all_living
        self.vegetation.compute_plant_visibility(self.agents)

        occupied_tiles: set[Pos] = {a.pos for a in all_living}
        sleeping_tiles: set[Pos] = {a.pos for a in all_living if a.is_sleeping}

        self.agents.build_spatial_grid()

        self._process_agents(all_living, occupied_tiles, sleeping_tiles, is_night)

        events = event_bus.drain()

        self.world.weather.tick()

        return events
