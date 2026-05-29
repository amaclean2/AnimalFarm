import math

from pydantic import BaseModel

import config as _cfg
from config import (
    MAX_HUNGER,
    MAX_WATER,
    MAX_REST,
    MAX_WARMTH,
    REST_THRESHOLD,
    NIGHT_DRAIN,
    REST_DRAIN,
    REST_RESTORE,
    WATER_DRAIN,
    WATER_DRAIN_MULTIPLIER,
    WARMTH_EXPOSED_DRAIN,
    WARMTH_SHELTERED_DRAIN,
    WARMTH_RESTORE,
    INFANT_DRAIN,
    EAT_RESTORE,
    DRINK_RESTORE,
    LONE_HUNGER_PENALTY,
    SLEEP_HUNGER_OVERRIDE,
    REPRODUCTION_HUNGER_THRESHOLD,
)


class NeedState(BaseModel):
    hunger: int = MAX_HUNGER
    water: int = MAX_WATER
    warmth: float = MAX_WARMTH
    rest: int = MAX_REST
    is_sleeping: bool = False
    rest_threshold: int = REST_THRESHOLD
    night_drain: int = NIGHT_DRAIN
    metabolism: float = 1.0
    hunger_override: int = SLEEP_HUNGER_OVERRIDE

    def tick(
        self, is_night: bool, on_exposed_tile: bool, age: int, is_adult: bool
    ) -> None:
        self._tick_rest(is_night)
        if is_night:
            drain = WARMTH_EXPOSED_DRAIN if on_exposed_tile else WARMTH_SHELTERED_DRAIN
            self.warmth = max(0.0, self.warmth - drain)
        else:
            self.warmth = min(MAX_WARMTH, self.warmth + WARMTH_RESTORE)
        if not self.is_sleeping:
            self.water = max(0, self.water - WATER_DRAIN)

    def _tick_rest(self, is_night: bool) -> None:
        if self.is_sleeping:
            self.rest = min(MAX_REST, self.rest + REST_RESTORE)
        elif is_night:
            self.rest = max(0, self.rest - self.night_drain)
        else:
            self.rest = max(0, self.rest - REST_DRAIN)
        if not self.is_sleeping and self.rest <= self.rest_threshold:
            self.is_sleeping = True
        elif self.is_sleeping and self.rest >= MAX_REST:
            self.is_sleeping = False

    def should_rest(self) -> bool:
        return self.is_sleeping and self.hunger > self.hunger_override

    def eat(self) -> None:
        self.hunger = min(MAX_HUNGER, self.hunger + EAT_RESTORE)

    def drink(self) -> None:
        self.water = min(MAX_WATER, self.water + DRINK_RESTORE)

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

    def urgency_vector(self, is_night: bool) -> dict[str, float]:
        h = self._hunger_urgency()
        t = self._thirst_urgency()
        r = self._rest_urgency()
        w = self._warmth_urgency(is_night)
        return {
            "hunger": h,
            "thirst": t,
            "rest": r,
            "warmth": w,
            "safety": 0.0,
            "social": 0.0,
            "reproduction": self._reproduction_urgency(),
            "curiosity": self._curiosity_urgency(h, t, r, w),
        }

    def _hunger_urgency(self) -> float:
        return min(1.0, (1.0 - self.hunger / MAX_HUNGER) ** 0.5)

    def _thirst_urgency(self) -> float:
        return min(1.0, (1.0 - self.water / MAX_WATER) ** 2)

    def _rest_urgency(self) -> float:
        return self._logistic(1.0 - self.rest / MAX_REST, steepness=10, midpoint=0.6)

    def _warmth_urgency(self, is_night: bool) -> float:
        if not is_night:
            return 0.0
        return self._logistic(
            1.0 - self.warmth / MAX_WARMTH, steepness=10, midpoint=0.5
        )

    def _reproduction_urgency(self) -> float:
        floor = MAX_HUNGER * REPRODUCTION_HUNGER_THRESHOLD
        if self.hunger < floor:
            return 0.0
        return (self.hunger - floor) / (MAX_HUNGER - floor)

    def _curiosity_urgency(self, h: float, t: float, r: float, w: float) -> float:
        return max(0.0, 1.0 - max(h, t, r, w) * 2.0)

    @staticmethod
    def _logistic(x: float, steepness: float, midpoint: float) -> float:
        return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))
