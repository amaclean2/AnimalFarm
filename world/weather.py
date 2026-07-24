import math
from collections.abc import Callable

from config import (
    CLIMATE_COARSE_SCALE,
    CLIMATE_MEDIUM_SCALE,
    DIURNAL_AMPLITUDE,
    TEMP_ELEVATION_COUPLING,
)
from noise import value_noise_2d


class WeatherSystem:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._temperature: list[float] = []
        self._precipitation: list[float] = []
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

        self.rebuild_temperature_grid()

    def diurnal_offset(self) -> float:
        return DIURNAL_AMPLITUDE * math.cos(2 * math.pi * (self._day_phase - 0.25))

    def get_temperature_at(self, x: int, y: int) -> float:
        if not self._temperature:
            return 0.5
        base = self._temperature[y * self.width + x]
        return max(0.0, min(1.0, base + self.diurnal_offset()))

    def get_precipitation_at(self, x: int, y: int) -> float:
        if not self._precipitation:
            return 0.5
        return self._precipitation[y * self.width + x]

    def base_temperature(self) -> list[float]:
        return self._temperature

    def base_precipitation(self) -> list[float]:
        return self._precipitation

    def reset(self) -> None:
        self._temperature.clear()
        self._precipitation.clear()
        self.temperature_grid = []
