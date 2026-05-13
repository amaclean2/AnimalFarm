from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Home(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x: int
    y: int
    agent_id: UUID
