from pydantic import BaseModel

from config import (
    HUNGER_BASE_DRAIN,
    HUNGER_INFANT_MULTIPLIER,
    HUNGER_RIVER_MULTIPLIER,
    HILL_ENERGY_MULTIPLIER,
    EAT_RESTORE,
    MATURITY_AGE,
    WATER_BASE_DRAIN,
    DRINK_RESTORE,
    REST_BASE_DRAIN,
    REST_NIGHT_MULTIPLIER,
    REST_COLD_MULTIPLIER,
    REST_RESTORE_MIN,
    REST_RESTORE_MAX,
    TEMP_MIN_C,
    TEMP_MAX_C,
    DRAIN_RATE_MULTIPLIER,
)


class NeedState(BaseModel):
    hunger: float = 1.0
    water: float = 1.0
    rest: float = 1.0
    is_sleeping: bool = False
    is_drinking: bool = False
    harvest_count: int = 0
    night_drain_multiplier: float = REST_NIGHT_MULTIPLIER
    metabolism: float = 1.0
    water_drain_rate: float = WATER_BASE_DRAIN
    rest_drain_rate: float = REST_BASE_DRAIN
    hunger_drain_rate: float = HUNGER_BASE_DRAIN

    @property
    def is_busy(self) -> bool:
        return self.is_sleeping or self.harvest_count > 0 or self.is_drinking

    def get_ticks_to_empty(self, need: str) -> int:
        drain_map = {
            "hunger": self.hunger_drain_rate,
            "water": self.water_drain_rate,
            "rest": self.rest_drain_rate,
        }
        level = getattr(self, need)
        rate = drain_map[need] * DRAIN_RATE_MULTIPLIER
        return int(level / rate) if rate > 0 else 0

    def apply_thirst_drain(self) -> None:
        self.water = max(
            0.0, self.water - (self.water_drain_rate * DRAIN_RATE_MULTIPLIER)
        )

    def apply_rest_drain(self, temperature: float = 15.0) -> None:
        base = self.rest_drain_rate * DRAIN_RATE_MULTIPLIER
        temp_norm = (temperature - TEMP_MIN_C) / (TEMP_MAX_C - TEMP_MIN_C)
        cold_mult = 1.0 + (REST_COLD_MULTIPLIER - 1.0) * (1.0 - temp_norm)
        self.rest = max(0.0, self.rest - base * cold_mult)

    def drain_uphill(self, elev_gain: float) -> None:
        extra = elev_gain * HILL_ENERGY_MULTIPLIER * HUNGER_BASE_DRAIN

        if extra > 0:
            self.hunger = max(0.0, self.hunger - extra)

    def apply_hunger_drain(self, age: int, is_river: bool) -> None:
        if age >= MATURITY_AGE:
            age_mult = 1.0
        else:
            t = min(age, MATURITY_AGE) / MATURITY_AGE
            age_mult = HUNGER_INFANT_MULTIPLIER + (1.0 - HUNGER_INFANT_MULTIPLIER) * t

        base = (
            self.hunger_drain_rate * age_mult * self.metabolism * DRAIN_RATE_MULTIPLIER
        )
        river_mult = HUNGER_RIVER_MULTIPLIER if is_river else 1.0
        self.hunger -= base * river_mult

    def sleep(self, tile_quality: float = 1.0) -> bool:
        restore = REST_RESTORE_MIN + tile_quality * (
            REST_RESTORE_MAX - REST_RESTORE_MIN
        )
        self.rest = min(1.0, self.rest + restore)

        if self.rest >= 1.0:
            self.is_sleeping = False
            return True

        return False

    def harvest(self) -> None:
        self.harvest_count -= 1

    def eat(self) -> None:
        self.hunger = min(1.0, self.hunger + EAT_RESTORE)

    def drink(self) -> None:
        self.water = min(1.0, self.water + DRINK_RESTORE)
        self.is_drinking = False
