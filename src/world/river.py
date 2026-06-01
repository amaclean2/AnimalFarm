from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PrivateAttr

from pos import Pos


class River(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tiles: list[Pos] = Field(default_factory=list)
    complete: bool = False
    pool_level: float = 0.0
    last_dx: int = 0
    last_dy: int = 0

    _tile_set: set[Pos] = PrivateAttr(default_factory=set)

    def model_post_init(self, __context: Any) -> None:
        self._tile_set = set(self.tiles)

    def add_tile(self, pos: Pos) -> None:
        self.tiles.append(pos)
        self._tile_set.add(pos)

    def contains_tile(self, pos: Pos) -> bool:
        return pos in self._tile_set

    @property
    def head(self) -> Pos | None:
        return self.tiles[-1] if self.tiles else None


class Rivers:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._data: dict[UUID, River] = {}
        self._tile_set: set[Pos] = set()

    def add_spring(self, pos: Pos) -> River:
        if not (0 <= pos.x < self._width and 0 <= pos.y < self._height):
            raise ValueError(f"Position {pos} is out of bounds")
        river = River(tiles=[pos])
        self._data[river.id] = river
        self._tile_set.add(pos)
        return river

    def extend(self, river: River, pos: Pos) -> None:
        river.add_tile(pos)
        self._tile_set.add(pos)
        if (
            pos.x == 0
            or pos.x >= self._width - 1
            or pos.y == 0
            or pos.y >= self._height - 1
        ):
            river.complete = True

    def is_river_tile(self, pos: Pos) -> bool:
        return pos in self._tile_set

    @property
    def all_rivers(self) -> list[River]:
        return list(self._data.values())

    @property
    def all_tiles(self) -> set[Pos]:
        return self._tile_set

    def clear(self) -> None:
        self._data.clear()
        self._tile_set.clear()
