import math

from pydantic import BaseModel

import config as _cfg
from config import (
    MAX_HUNGER,
    MAX_WATER,
    MAX_REST,
    NIGHT_DRAIN,
    REST_DRAIN,
    REST_RESTORE_MIN,
    REST_RESTORE_MAX,
    WATER_DRAIN,
    WATER_DRAIN_MULTIPLIER,
    INFANT_DRAIN,
    EAT_RESTORE,
    DRINK_RESTORE,
    LONE_HUNGER_PENALTY,
    REPRODUCTION_HUNGER_THRESHOLD,
    HILL_ENERGY_SCALE,
)


class NeedState(BaseModel):
    hunger: int = MAX_HUNGER
    water: int = MAX_WATER
    rest: int = MAX_REST
    is_sleeping: bool = False
    night_drain: int = NIGHT_DRAIN
    metabolism: float = 1.0

    def tick(
        self,
        is_night: bool,
        tile_quality: float = 1.0,
    ) -> None:
        self._tick_rest(is_night, tile_quality)

        if not self.is_sleeping:
            self.water = max(0, self.water - WATER_DRAIN)

    def _tick_rest(self, is_night: bool, tile_quality: float = 1.0) -> None:
        if self.is_sleeping:
            restore = round(
                REST_RESTORE_MIN + tile_quality * (REST_RESTORE_MAX - REST_RESTORE_MIN)
            )
            self.rest = min(MAX_REST, self.rest + restore)
        elif is_night:
            self.rest = max(0, self.rest - self.night_drain)
        else:
            self.rest = max(0, self.rest - REST_DRAIN)

    def eat(self) -> None:
        self.hunger = min(MAX_HUNGER, self.hunger + EAT_RESTORE)

    def drink(self) -> None:
        self.water = min(MAX_WATER, self.water + DRINK_RESTORE)

    def drain_uphill(self, elev_gain: float) -> None:
        extra = round(elev_gain * HILL_ENERGY_SCALE)

        if extra > 0:
            self.hunger = max(0, self.hunger - extra)

    def apply_hunger_drain(
        self, age: int, is_adult: bool, is_river: bool, is_lone: bool
    ) -> None:
        if is_adult:
            base_drain = _cfg.ADULT_DRAIN
        else:
            t = min(age, _cfg.MATURITY_AGE) / _cfg.MATURITY_AGE
            base_drain = max(1, round(INFANT_DRAIN + (1 - INFANT_DRAIN) * t))
        base = round(base_drain * self.metabolism)
        water_penalty = base * (WATER_DRAIN_MULTIPLIER - 1) if is_river else 0
        lone_penalty = LONE_HUNGER_PENALTY if is_lone else 0
        self.hunger -= base + water_penalty + lone_penalty

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
        return min(1.0, (1.0 - self.hunger / MAX_HUNGER) ** 0.5)

    def _thirst_urgency(self) -> float:
        return min(1.0, (1.0 - self.water / MAX_WATER) ** 2)

    def _rest_urgency(self) -> float:
        return self._logistic(1.0 - self.rest / MAX_REST, steepness=10, midpoint=0.6)

    def _reproduction_urgency(self) -> float:
        floor = MAX_HUNGER * REPRODUCTION_HUNGER_THRESHOLD

        if self.hunger < floor:
            return 0.0
        return (self.hunger - floor) / (MAX_HUNGER - floor)

    def _curiosity_urgency(self, h: float, t: float, r: float) -> float:
        return max(0.0, 1.0 - max(h, t, r) * 2.0)

    @staticmethod
    def _logistic(x: float, steepness: float, midpoint: float) -> float:
        return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))
