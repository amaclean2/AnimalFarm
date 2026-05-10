from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class River(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tiles: list[tuple[int, int]] = Field(default_factory=list)
    complete: bool = False

    @property
    def head(self) -> tuple[int, int] | None:
        return self.tiles[-1] if self.tiles else None
