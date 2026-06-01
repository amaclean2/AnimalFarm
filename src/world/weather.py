import math
import random
from collections.abc import Callable

from config import (
    CLIMATE_COARSE_SCALE,
    CLIMATE_MEDIUM_SCALE,
    CLOUD_COUNT,
    CLOUD_LIFESPAN_MAX,
    CLOUD_LIFESPAN_MIN,
    CLOUD_PRECIP_STRENGTH,
    CLOUD_RADIUS_MAX,
    CLOUD_RADIUS_MIN,
    CLOUD_SPEED_MAX,
    CLOUD_TEMP_REDUCTION,
    DIURNAL_AMPLITUDE,
    TEMP_ELEVATION_COUPLING,
)
from noise import value_noise_2d


class Cloud:
    def __init__(
        self,
        cx: float,
        cy: float,
        radius: float,
        lifespan: int,
        vx: float,
        vy: float,
    ) -> None:
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.lifespan = lifespan
        self.vx = vx
        self.vy = vy
        self.age = 0

    @property
    def strength(self) -> float:
        frac = self.age / self.lifespan
        ramp = 0.2
        if frac < ramp:
            t = frac / ramp
        elif frac > (1.0 - ramp):
            t = (1.0 - frac) / ramp
        else:
            return 1.0
        return t * t * (3.0 - 2.0 * t)

    @property
    def dead(self) -> bool:
        return self.age >= self.lifespan

    def tick(self, width: int, height: int) -> None:
        self.cx = (self.cx + self.vx) % width
        self.cy = (self.cy + self.vy) % height
        self.age += 1

    def contribution_at(self, x: int, y: int, width: int, height: int) -> float:
        dx = min(abs(x - self.cx), width - abs(x - self.cx))
        dy = min(abs(y - self.cy), height - abs(y - self.cy))
        dist = math.sqrt(dx * dx + dy * dy)
        if dist >= self.radius:
            return 0.0
        t = 1.0 - dist / self.radius
        falloff = t * t * (3.0 - 2.0 * t)
        return falloff * self.strength


class CloudSystem:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._clouds: list[Cloud] = []

    def _spawn(self) -> Cloud:
        radius = random.uniform(CLOUD_RADIUS_MIN, CLOUD_RADIUS_MAX)
        lifespan = random.randint(CLOUD_LIFESPAN_MIN, CLOUD_LIFESPAN_MAX)
        cx = random.uniform(0, self.width)
        cy = random.uniform(0, self.height)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.05, CLOUD_SPEED_MAX)
        cloud = Cloud(
            cx, cy, radius, lifespan, math.cos(angle) * speed, math.sin(angle) * speed
        )
        self._clouds.append(cloud)
        return cloud

    def seed(self) -> None:
        for _ in range(CLOUD_COUNT):
            cloud = self._spawn()
            cloud.age = random.randint(0, cloud.lifespan * 3 // 4)

    def tick(self) -> None:
        for cloud in self._clouds:
            cloud.tick(self.width, self.height)
        self._clouds = [c for c in self._clouds if not c.dead]
        while len(self._clouds) < CLOUD_COUNT:
            self._spawn()

    def _get_precipitation_at(self, x: int, y: int, base: float) -> float:
        total = sum(
            c.contribution_at(x, y, self.width, self.height) for c in self._clouds
        )
        return min(1.0, base + CLOUD_PRECIP_STRENGTH * min(1.0, total))

    def _get_temperature_at(self, x: int, y: int, base: float) -> float:
        total = sum(
            c.contribution_at(x, y, self.width, self.height) for c in self._clouds
        )
        return max(0.0, base - CLOUD_TEMP_REDUCTION * min(1.0, total))

    def to_list(self) -> list[dict]:
        return [
            {
                "cx": round(c.cx, 2),
                "cy": round(c.cy, 2),
                "radius": round(c.radius, 2),
                "strength": round(c.strength, 3),
            }
            for c in self._clouds
        ]

    def reset(self) -> None:
        self._clouds.clear()


class WeatherSystem:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._temperature: list[float] = []
        self._precipitation: list[float] = []
        self._clouds = CloudSystem(width, height)
        self._day_phase: float = 0.0
        self.temperature_grid: list[float] = []

    def set_day_phase(self, phase: float) -> None:
        self._day_phase = phase
        if self._temperature:
            self.rebuild_temperature_grid()

    def rebuild_temperature_grid(self) -> None:
        self.temperature_grid = [
            self.get_temperature_at(x, y)
            for y in range(self.height)
            for x in range(self.width)
        ]

    def generate(self, seed: int, elevation_at: Callable[[int, int], float]) -> None:
        self._temperature = []
        self._precipitation = []
        for y in range(self.height):
            for x in range(self.width):
                raw_temp = 0.8 * value_noise_2d(
                    x, y, CLIMATE_COARSE_SCALE, seed + 100000
                ) + 0.2 * value_noise_2d(x, y, CLIMATE_MEDIUM_SCALE, seed + 200000)
                temp = raw_temp * (1.0 - TEMP_ELEVATION_COUPLING * elevation_at(x, y))
                self._temperature.append(max(0.0, min(1.0, temp)))

                precip = 0.75 * value_noise_2d(
                    x, y, CLIMATE_COARSE_SCALE, seed + 300000
                ) + 0.25 * value_noise_2d(x, y, CLIMATE_MEDIUM_SCALE, seed + 400000)
                self._precipitation.append(max(0.0, min(1.0, precip)))

        self._clouds.reset()
        self._clouds.seed()
        self.rebuild_temperature_grid()

    def tick(self) -> None:
        self._clouds.tick()

    def diurnal_offset(self) -> float:
        return DIURNAL_AMPLITUDE * math.cos(2 * math.pi * (self._day_phase - 0.25))

    def get_temperature_at(self, x: int, y: int) -> float:
        if not self._temperature:
            return 0.5
        base = self._temperature[y * self.width + x]
        cloud_adjusted = self._clouds._get_temperature_at(x, y, base)
        return max(0.0, min(1.0, cloud_adjusted + self.diurnal_offset()))

    def get_precipitation_at(self, x: int, y: int) -> float:
        if not self._precipitation:
            return 0.5
        base = self._precipitation[y * self.width + x]
        return self._clouds._get_precipitation_at(x, y, base)

    def base_temperature(self) -> list[float]:
        return self._temperature

    def base_precipitation(self) -> list[float]:
        return self._precipitation

    def clouds_to_list(self) -> list[dict]:
        return self._clouds.to_list()

    def reset(self) -> None:
        self._temperature.clear()
        self._precipitation.clear()
        self._clouds.reset()
        self.temperature_grid = []
