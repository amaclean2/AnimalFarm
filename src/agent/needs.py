import math

from pydantic import BaseModel

import config as _cfg
from config import (
    HUNGER_BASE_DRAIN,
    HUNGER_INFANT_MULTIPLIER,
    HUNGER_RIVER_MULTIPLIER,
    HUNGER_LONE_MULTIPLIER,
    HILL_ENERGY_MULTIPLIER,
    EAT_RESTORE,
    WATER_BASE_DRAIN,
    DRINK_RESTORE,
    REST_BASE_DRAIN,
    REST_NIGHT_MULTIPLIER,
    REST_COLD_MULTIPLIER,
    REST_RESTORE_MIN,
    REST_RESTORE_MAX,
    REPRODUCTION_HUNGER_THRESHOLD,
)


class NeedState(BaseModel):
    hunger: float = 1.0
    water: float = 1.0
    rest: float = 1.0
    is_sleeping: bool = False
    night_drain_multiplier: float = REST_NIGHT_MULTIPLIER
    metabolism: float = 1.0

    def tick(
        self,
        is_night: bool,
        tile_quality: float = 1.0,
        temperature: float = 0.5,
    ) -> None:
        self._tick_rest(is_night, tile_quality, temperature)

        if not self.is_sleeping:
            self.water = max(0.0, self.water - WATER_BASE_DRAIN)

    def _tick_rest(
        self, is_night: bool, tile_quality: float = 1.0, temperature: float = 0.5
    ) -> None:
        if self.is_sleeping:
            restore = REST_RESTORE_MIN + tile_quality * (
                REST_RESTORE_MAX - REST_RESTORE_MIN
            )
            self.rest = min(1.0, self.rest + restore)
        else:
            base = REST_BASE_DRAIN * (self.night_drain_multiplier if is_night else 1.0)
            cold_mult = 1.0 + (REST_COLD_MULTIPLIER - 1.0) * (1.0 - temperature)
            self.rest = max(0.0, self.rest - base * cold_mult)

    def eat(self) -> None:
        self.hunger = min(1.0, self.hunger + EAT_RESTORE)

    def drink(self) -> None:
        self.water = min(1.0, self.water + DRINK_RESTORE)

    def drain_uphill(self, elev_gain: float) -> None:
        extra = elev_gain * HILL_ENERGY_MULTIPLIER * HUNGER_BASE_DRAIN

        if extra > 0:
            self.hunger = max(0.0, self.hunger - extra)

    def apply_hunger_drain(
        self, age: int, is_adult: bool, is_river: bool, is_lone: bool
    ) -> None:
        if is_adult:
            age_mult = 1.0
        else:
            t = min(age, _cfg.MATURITY_AGE) / _cfg.MATURITY_AGE
            age_mult = HUNGER_INFANT_MULTIPLIER + (1.0 - HUNGER_INFANT_MULTIPLIER) * t
        base = HUNGER_BASE_DRAIN * age_mult * self.metabolism
        river_mult = HUNGER_RIVER_MULTIPLIER if is_river else 1.0
        lone_mult = HUNGER_LONE_MULTIPLIER if is_lone else 1.0
        self.hunger -= base * river_mult * lone_mult

    def urgency_vector(self) -> dict[str, float]:
        h = self._hunger_urgency()
        t = self._thirst_urgency()
        r = self._rest_urgency()
        return {
            "hunger": h,
            "thirst": t,
            "rest": r,
            "safety": 0.0,
            "social": 0.0,
            "reproduction": self._reproduction_urgency(),
            "curiosity": self._curiosity_urgency(h, t, r),
        }

    def _hunger_urgency(self) -> float:
        return min(1.0, (1.0 - self.hunger) ** 0.5)

    def _thirst_urgency(self) -> float:
        return min(1.0, (1.0 - self.water) ** 2)

    def _rest_urgency(self) -> float:
        return self._logistic(1.0 - self.rest, steepness=10, midpoint=0.6)

    def _reproduction_urgency(self) -> float:
        if self.hunger < REPRODUCTION_HUNGER_THRESHOLD:
            return 0.0
        t = (self.hunger - REPRODUCTION_HUNGER_THRESHOLD) / (
            1.0 - REPRODUCTION_HUNGER_THRESHOLD
        )
        return t**0.5

    def _curiosity_urgency(self, h: float, t: float, r: float) -> float:
        return max(0.0, 1.0 - max(h, t, r) * 2.0)

    @staticmethod
    def _logistic(x: float, steepness: float, midpoint: float) -> float:
        return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))
