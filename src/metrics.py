import json
from datetime import datetime, timezone
from pathlib import Path

from agent import MAX_HEALTH

LOGS_DIR = Path(__file__).parent.parent / "logs"
BIRTH_RATE_WINDOW = 20


class SimulationMetrics:
    def __init__(self, max_age: int) -> None:
        self._max_age = max_age
        self._ticks: int = 0
        self._births: int = 0
        self._window_births: int = 0
        self._birth_history: list[int] = []
        self._starvation_deaths: int = 0
        self._age_deaths: int = 0
        self._food_eaten: int = 0
        self._food_stockpiled: int = 0
        self._food_withdrawn: int = 0
        self._groups_formed: int = 0
        self._groups_disbanded: int = 0
        self._peak_population: int = 0
        self._peak_group_count: int = 0
        self._agent_ticks_alive: int = 0
        self._agent_ticks_in_group: int = 0
        self._total_health_sum: int = 0
        self._agent_ticks_full_health: int = 0
        self._total_food_sum: int = 0
        self._min_food_per_tick: int | None = None
        self._reproduction_eligible_pairs: int = 0
        self._mutation_births: dict[str, int] = {}
        self._mutation_deaths: dict[str, int] = {}
        self._mutation_age_sum: dict[str, int] = {}
        self._mutation_pop_window: dict[str, int] = {}
        self._mutation_pop_history: dict[str, list[float]] = {}
        self._population_window: int = 0
        self._population_history: list[float] = []
        self._window_count: int = 0

    def reset(self) -> None:
        self._ticks = 0
        self._births = 0
        self._starvation_deaths = 0
        self._age_deaths = 0
        self._food_eaten = 0
        self._food_stockpiled = 0
        self._food_withdrawn = 0
        self._groups_formed = 0
        self._groups_disbanded = 0
        self._peak_population = 0
        self._peak_group_count = 0
        self._agent_ticks_alive = 0
        self._agent_ticks_in_group = 0
        self._total_health_sum = 0
        self._agent_ticks_full_health = 0
        self._total_food_sum = 0
        self._min_food_per_tick = None
        self._reproduction_eligible_pairs = 0
        self._mutation_births = {}
        self._mutation_deaths = {}
        self._mutation_age_sum = {}
        self._mutation_pop_window = {}
        self._mutation_pop_history = {}
        self._population_window = 0
        self._population_history = []
        self._window_count = 0
        self._window_births = 0
        self._birth_history = []

    def record_tick(self, living: list, group_count: int, food_count: int, eligible_pairs: int = 0) -> None:
        self._ticks += 1
        n = len(living)
        
        self._peak_population = max(self._peak_population, n)
        self._peak_group_count = max(self._peak_group_count, group_count)
        self._agent_ticks_alive += n
        self._agent_ticks_in_group += sum(1 for a in living if a.group_id is not None)
        self._total_health_sum += sum(a.health for a in living)
        self._agent_ticks_full_health += sum(1 for a in living if a.health == MAX_HEALTH)
        self._total_food_sum += food_count
        
        self._min_food_per_tick = (
            food_count if self._min_food_per_tick is None
            else min(self._min_food_per_tick, food_count)
        )
        
        self._reproduction_eligible_pairs += eligible_pairs
        
        for agent in living:
            for m in agent.mutations:
                self._mutation_pop_window[m] = self._mutation_pop_window.get(m, 0) + 1
        
        self._population_window += n
        
        if self._ticks % BIRTH_RATE_WINDOW == 0:
            self._birth_history.append(self._window_births)
            self._window_births = 0
            
            all_tracked = set(self._mutation_births) | set(self._mutation_pop_window) | set(self._mutation_pop_history)
            
            for m in all_tracked:
                history = self._mutation_pop_history.setdefault(m, [])
                while len(history) < self._window_count:
                    history.append(0.0)
                history.append(round(self._mutation_pop_window.get(m, 0) / BIRTH_RATE_WINDOW, 1))
            
            self._mutation_pop_window = {}
            self._population_history.append(round(self._population_window / BIRTH_RATE_WINDOW, 1))
            self._population_window = 0
            self._window_count += 1

    def record_event(self, event_type: str, data: dict) -> None:
        if event_type == "agent_born":
            self._births += 1
            self._window_births += 1
            
            for m in data["agent"].get("mutations", []):
                self._mutation_births[m] = self._mutation_births.get(m, 0) + 1
        
        elif event_type == "agent_died":
            if data["agent"]["age"] >= self._max_age:
                self._age_deaths += 1
            else:
                self._starvation_deaths += 1
                
            age = data["agent"]["age"]
            
            for m in data["agent"].get("mutations", []):
                self._mutation_deaths[m] = self._mutation_deaths.get(m, 0) + 1
                self._mutation_age_sum[m] = self._mutation_age_sum.get(m, 0) + age
        
        elif event_type == "agent_ate":
            self._food_eaten += 1
        elif event_type == "food_deposited":
            self._food_stockpiled += 1
        elif event_type == "food_withdrawn":
            self._food_withdrawn += 1
        elif event_type == "group_formed":
            self._groups_formed += 1
        elif event_type == "group_disbanded":
            self._groups_disbanded += 1

    def write_game_log(self) -> None:
        LOGS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = LOGS_DIR / f"game_{timestamp}.json"

        alive = self._agent_ticks_alive
        participation = self._agent_ticks_in_group / alive if alive > 0 else 0.0
        avg_health = round(self._total_health_sum / alive, 1) if alive > 0 else 0.0
        pct_full_health = round(self._agent_ticks_full_health / alive, 3) if alive > 0 else 0.0
        avg_food = round(self._total_food_sum / self._ticks, 1) if self._ticks > 0 else 0.0
        eligible = self._reproduction_eligible_pairs

        data = {
            "game_summary": {
                "ticks_survived": self._ticks,
                "peak_population": self._peak_population,
                "peak_group_count": self._peak_group_count,
            },
            "population": {
                "total_births": self._births,
                "starvation_deaths": self._starvation_deaths,
                "age_deaths": self._age_deaths,
                "history": self._population_history,
            },
            "health": {
                "avg_health_per_agent": avg_health,
                "avg_health_pct": round(avg_health / MAX_HEALTH, 3),
                "pct_ticks_at_full_health": pct_full_health,
            },
            "food": {
                "total_eaten": self._food_eaten,
                "total_stockpiled": self._food_stockpiled,
                "total_withdrawn": self._food_withdrawn,
                "avg_food_tiles_per_tick": avg_food,
                "min_food_tiles_per_tick": self._min_food_per_tick if self._min_food_per_tick is not None else 0,
            },
            "reproduction": {
                "eligible_pairs_found": eligible,
                "births": self._births,
                "conversion_rate": round(self._births / eligible, 3) if eligible > 0 else 0.0,
                "birth_rate_history": self._birth_history,
                "birth_rate_window_ticks": BIRTH_RATE_WINDOW,
            },
            "social": {
                "groups_formed": self._groups_formed,
                "groups_disbanded": self._groups_disbanded,
                "agent_ticks_in_group": self._agent_ticks_in_group,
                "total_agent_ticks": alive,
                "group_participation_rate": round(participation, 3),
            },
        }

        mutation_stats: dict[str, dict] = {}
        all_mutations = (
            set(self._mutation_births)
            | set(self._mutation_deaths)
            | set(self._mutation_pop_history)
        )
        n_windows = len(self._population_history)

        for name in all_mutations:
            births = self._mutation_births.get(name, 0)
            deaths = self._mutation_deaths.get(name, 0)
            pop_history = self._mutation_pop_history.get(name, [])

            pad = n_windows - len(pop_history)
            padded = [0.0] * pad + pop_history
            diversity_history = [
                round(p / t, 3) if t > 0 else 0.0
                for p, t in zip(padded, self._population_history)
            ]

            mutation_stats[name] = {
                "births": births,
                "deaths": deaths,
                "alive": max(0, births - deaths),
                "avg_age_at_death": (
                    round(self._mutation_age_sum.get(name, 0) / deaths, 1)
                    if deaths > 0 else None
                ),
                "population_history": pop_history,
                "diversity_history": diversity_history,
            }

        if mutation_stats:
            data["mutations"] = mutation_stats

        path.write_text(json.dumps(data, indent=2))
