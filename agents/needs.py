from pydantic import BaseModel

from config import (
    INFANT_DRAIN_PENALTY,
    HUNGER_RIVER_MULTIPLIER,
    HILL_ENERGY_MULTIPLIER,
    DRINK_RESTORE,
    REST_RESTORE_MIN,
    REST_RESTORE_MAX,
    DRAIN_RATE_MULTIPLIER,
    IDEAL_CORE_TEMP_C,
    CORE_TEMP_DEATH_MARGIN_C,
    CORE_TEMP_DRIFT_RATE,
)
from genome import GENE_DEFAULTS


class NeedState(BaseModel):
    hunger: float = 0.0
    water: float = 0.0
    rest: float = 0.0
    is_sleeping: bool = False
    is_drinking: bool = False
    is_eating: bool = False
    is_harvesting: bool = False
    harvest_progress: float = 0.0
    harvest_rate: float = 0.0
    eat_restore: float = 0.0
    water_drain_rate: float = GENE_DEFAULTS["water_drain_rate"]
    rest_drain_rate: float = GENE_DEFAULTS["rest_drain_rate"]
    hunger_drain_rate: float = GENE_DEFAULTS["hunger_drain_rate"]
    core_temperature: float = IDEAL_CORE_TEMP_C

    @property
    def is_busy(self) -> bool:
        return (
            self.is_sleeping or self.is_harvesting or self.is_drinking or self.is_eating
        )

    def get_ticks_to_empty(self, need: str) -> int:
        drain_map = {
            "hunger": self.hunger_drain_rate,
            "water": self.water_drain_rate,
            "rest": self.rest_drain_rate,
        }
        level = getattr(self, need)
        rate = drain_map[need] * DRAIN_RATE_MULTIPLIER
        return int((1.0 - level) / rate) if rate > 0 else 0

    @staticmethod
    def _infant_drain_mult(age: int) -> float:
        return 1.0 + INFANT_DRAIN_PENALTY / (0.08 * age + 1)

    def apply_thirst_drain(self, age: int) -> None:
        age_mult = self._infant_drain_mult(age)
        base_drain = self.water_drain_rate * age_mult * DRAIN_RATE_MULTIPLIER

        off_from_core_temp = abs(self.core_temperature - IDEAL_CORE_TEMP_C)
        off_ratio = off_from_core_temp / CORE_TEMP_DEATH_MARGIN_C

        heat_mult = off_ratio**2

        self.water = min(1.0, self.water + base_drain * heat_mult)

    def apply_rest_drain(self, age: int) -> None:
        age_mult = self._infant_drain_mult(age)
        self.rest = min(
            1.0, self.rest + (self.rest_drain_rate * age_mult * DRAIN_RATE_MULTIPLIER)
        )

    def apply_temperature_drift(self, ambient_temperature: float) -> None:
        self.core_temperature += (
            ambient_temperature - self.core_temperature
        ) * CORE_TEMP_DRIFT_RATE

    def drain_uphill(self, elev_gain: float) -> None:
        extra = elev_gain * HILL_ENERGY_MULTIPLIER * self.hunger_drain_rate

        if extra > 0:
            self.hunger = min(1.0, self.hunger + extra)

    def apply_hunger_drain(self, age: int, is_river: bool) -> None:
        age_mult = self._infant_drain_mult(age)
        base = self.hunger_drain_rate * age_mult * DRAIN_RATE_MULTIPLIER
        river_mult = HUNGER_RIVER_MULTIPLIER if is_river else 1.0
        self.hunger = min(1.0, self.hunger + base * river_mult)

    def sleep(self, tile_quality: float = 1.0) -> None:
        restore = REST_RESTORE_MIN + tile_quality * (
            REST_RESTORE_MAX - REST_RESTORE_MIN
        )
        self.rest = max(0.0, self.rest - restore)

        if self.rest <= 0.0:
            self.is_sleeping = False

    def start_harvest(self, fruit_per_tick: float, eat_restore: float) -> None:
        self.is_harvesting = True
        self.harvest_rate = fruit_per_tick
        self.eat_restore = eat_restore

    def stop_harvest(self) -> None:
        self.is_harvesting = False
        self.harvest_progress = float(int(self.harvest_progress))

    def harvest(self, skill: float = 1.0) -> None:
        before = int(self.harvest_progress)
        self.harvest_progress += self.harvest_rate * skill

        if int(self.harvest_progress) != before:
            self.is_harvesting = False

    def eat(self) -> None:
        self.hunger = max(0.0, self.hunger - self.eat_restore)
        self.is_eating = False

    def drink(self) -> None:
        self.water = max(0.0, self.water - DRINK_RESTORE)
        self.is_drinking = False
