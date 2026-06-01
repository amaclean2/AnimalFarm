from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PrivateAttr

from pos import Pos

_TILE_BUCKET = 10


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
        self._bucket_index: dict[tuple[int, int], list[Pos]] = {}

    def _index_tile(self, pos: Pos) -> None:
        key = (pos.x // _TILE_BUCKET, pos.y // _TILE_BUCKET)
        self._bucket_index.setdefault(key, []).append(pos)

    def tiles_near(self, x: int, y: int, radius: int) -> list[Pos]:
        bx0 = (x - radius) // _TILE_BUCKET
        bx1 = (x + radius) // _TILE_BUCKET
        by0 = (y - radius) // _TILE_BUCKET
        by1 = (y + radius) // _TILE_BUCKET
        result = []

        for bx in range(bx0, bx1 + 1):
            for by in range(by0, by1 + 1):
                for pos in self._bucket_index.get((bx, by), []):
                    if abs(pos.x - x) + abs(pos.y - y) <= radius:
                        result.append(pos)

        return result

    def add_spring(self, pos: Pos) -> River:
        if not (0 <= pos.x < self._width and 0 <= pos.y < self._height):
            raise ValueError(f"Position {pos} is out of bounds")
        river = River(tiles=[pos])
        self._data[river.id] = river
        self._tile_set.add(pos)
        self._index_tile(pos)
        return river

    def extend(self, river: River, pos: Pos) -> None:
        river.add_tile(pos)
        self._tile_set.add(pos)
        self._index_tile(pos)

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
        self._bucket_index.clear()
