from pydantic import BaseModel

import config as _cfg
from config import (
    HUNGER_BASE_DRAIN,
    HUNGER_INFANT_MULTIPLIER,
    HUNGER_RIVER_MULTIPLIER,
    HILL_ENERGY_MULTIPLIER,
    EAT_RESTORE,
    WATER_BASE_DRAIN,
    DRINK_RESTORE,
    REST_BASE_DRAIN,
    REST_NIGHT_MULTIPLIER,
    REST_COLD_MULTIPLIER,
    REST_RESTORE_MIN,
    REST_RESTORE_MAX,
    TEMP_MIN_C,
    TEMP_MAX_C,
)


class NeedState(BaseModel):
    hunger: float = 1.0
    water: float = 1.0
    rest: float = 1.0
    is_sleeping: bool = False
    night_drain_multiplier: float = REST_NIGHT_MULTIPLIER
    metabolism: float = 1.0
    water_drain_rate: float = WATER_BASE_DRAIN
    rest_drain_rate: float = REST_BASE_DRAIN

    def tick(
        self,
        is_night: bool,
        tile_quality: float = 1.0,
        temperature: float = 15.0,
    ) -> None:
        self._tick_rest(is_night, tile_quality, temperature)

        if not self.is_sleeping:
            self.water = max(0.0, self.water - self.water_drain_rate)

    def _tick_rest(
        self, is_night: bool, tile_quality: float = 1.0, temperature: float = 15.0
    ) -> None:
        if self.is_sleeping:
            restore = REST_RESTORE_MIN + tile_quality * (
                REST_RESTORE_MAX - REST_RESTORE_MIN
            )
            self.rest = min(1.0, self.rest + restore)
        else:
            base = self.rest_drain_rate * (
                self.night_drain_multiplier if is_night else 1.0
            )
            temp_norm = (temperature - TEMP_MIN_C) / (TEMP_MAX_C - TEMP_MIN_C)
            cold_mult = 1.0 + (REST_COLD_MULTIPLIER - 1.0) * (1.0 - temp_norm)
            self.rest = max(0.0, self.rest - base * cold_mult)

    def eat(self) -> None:
        self.hunger = min(1.0, self.hunger + EAT_RESTORE)

    def drink(self) -> None:
        self.water = min(1.0, self.water + DRINK_RESTORE)

    def drain_uphill(self, elev_gain: float) -> None:
        extra = elev_gain * HILL_ENERGY_MULTIPLIER * HUNGER_BASE_DRAIN

        if extra > 0:
            self.hunger = max(0.0, self.hunger - extra)

    def apply_hunger_drain(self, age: int, is_adult: bool, is_river: bool) -> None:
        if is_adult:
            age_mult = 1.0
        else:
            t = min(age, _cfg.MATURITY_AGE) / _cfg.MATURITY_AGE
            age_mult = HUNGER_INFANT_MULTIPLIER + (1.0 - HUNGER_INFANT_MULTIPLIER) * t
        base = HUNGER_BASE_DRAIN * age_mult * self.metabolism
        river_mult = HUNGER_RIVER_MULTIPLIER if is_river else 1.0
        self.hunger -= base * river_mult

    @staticmethod
    def need_urgency(level: float) -> float:
        return (1.0 - level) ** 2
