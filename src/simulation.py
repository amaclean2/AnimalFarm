import random
from dataclasses import dataclass
from uuid import uuid4

from agents import Agents
from agents.agent import Agent
from clock import DAY_LENGTH
from genome_pool import GenomePool
from plant import Plant, VegetationManager
from pos import Pos
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

    def _harvest_tick(self, agent: Agent) -> bool:
        finished_harvesting = agent.harvest()

        if not finished_harvesting:
            return False

        local_plant = self.vegetation.remove_fruit_at(agent.pos)

        if local_plant is None:
            return True

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

        visible_water = self.world.rivers.tiles_near(agent.pos, int(vision))

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
    ) -> None:
        moves = self.world.valid_moves(agent.pos)
        if not moves:
            return

        valid_moves = [m for m in moves if m not in occupied_tiles]
        if not valid_moves:
            return

        shade = self.vegetation.shade_at(agent.pos)
        temperature = cfg.temp_to_c(
            max(0.0, self.world.weather.temperature_grid[agent.get_pos_idx()] - shade)
        )
        tile_quality = self.world.rest_quality_at(agent.pos)

        if agent.needs.is_sleeping:
            agent.sleep(tile_quality)

        if agent.needs.harvest_count > 0:
            self._harvest_tick(agent)

        if agent.needs.is_drinking:
            agent.drink()

        if agent.needs.is_busy:
            agent.planned_steps = []
            agent.next_decision_tick = self.tick_count + 1
            return

        snapshot = self._build_vision_snapshot(agent, sleeping_tiles)
        vision = float(agent.vision_range)
        mate_pos = self.agents.find_mate_target(agent, vision, self.tick_count)
        at_river_tile = self.world.rivers.is_river_tile(agent.pos)
        local_plant = self.vegetation.fruiting_plant_at(agent.pos)

        agent.update_memory(
            food_targets=snapshot.food_targets,
            visible_water=snapshot.visible_water,
            visible_rest=snapshot.visible_rest,
            tick=self.tick_count,
        )

        agent.plan_steps(
            mate_pos=mate_pos,
            at_river_tile=at_river_tile,
            local_plant=local_plant,
            world=self.world,
            valid_moves=valid_moves,
            occupied_tiles=occupied_tiles,
            tick_count=self.tick_count,
        )

        agent.tick_movement(
            self.world.rivers.is_river_tile,
            occupied_tiles,
            self.tick_count,
            self.world.elevation_at,
            temperature,
        )

    def _execute_agent_step(
        self,
        agent: Agent,
        occupied_tiles: set[Pos],
    ) -> None:
        shade = self.vegetation.shade_at(agent.pos)
        temperature = cfg.temp_to_c(
            max(0.0, self.world.weather.temperature_grid[agent.get_pos_idx()] - shade)
        )
        tile_quality = self.world.rest_quality_at(agent.pos)

        if agent.needs.is_sleeping:
            agent.sleep(tile_quality)

        if agent.needs.harvest_count > 0:
            self._harvest_tick(agent)

        if agent.needs.is_drinking:
            agent.drink()

        if agent.needs.is_busy:
            agent.planned_steps.clear()
            agent.next_decision_tick = self.tick_count + 1
        else:
            agent.tick_movement(
                self.world.rivers.is_river_tile,
                occupied_tiles,
                self.tick_count,
                self.world.elevation_at,
                temperature,
            )

    def _process_agents(
        self,
        all_living: list,
        occupied_tiles: set,
        sleeping_tiles: set,
    ) -> None:
        # agents take turns making decisions. Half the agents make decisions on even number ticks
        # and the others make decisions on odd number ticks
        # All agents carry out two ticks per decision

        deciding_agents = [
            a for a in all_living if self.tick_count >= a.next_decision_tick
        ]
        executing_agents = [
            a for a in all_living if self.tick_count < a.next_decision_tick
        ]

        for agent in executing_agents:
            self._execute_agent_step(agent, occupied_tiles)

        for agent in deciding_agents:
            self._decide_agent_step(
                agent,
                occupied_tiles,
                sleeping_tiles,
            )

        dead = [a.id for a in all_living if a.should_die()]

        for agent_id in dead:
            if self._genome_pool is not None:
                agent = self.agents.get(agent_id)

                if agent:
                    self._genome_pool.record(agent, self._sim_id, self.tick_count)

            self.agents.process_agent_death(agent_id)

        self.agents.reproduce(self.world, self.tick_count)

    def on_tick(self, tick_count: int) -> list[Event]:
        self.tick_count = tick_count
        self.world.weather.set_day_phase((tick_count % DAY_LENGTH) / DAY_LENGTH)

        self.vegetation.grow_plants()

        all_living = self.agents.all_living
        self.vegetation.compute_plant_visibility(self.agents)

        occupied_tiles: set[Pos] = {a.pos for a in all_living}
        sleeping_tiles: set[Pos] = {a.pos for a in all_living if a.needs.is_sleeping}

        self.agents.build_spatial_grid()

        self._process_agents(all_living, occupied_tiles, sleeping_tiles)

        events = event_bus.drain()

        self.world.weather.tick()

        return events
