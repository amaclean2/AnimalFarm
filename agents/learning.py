from pydantic import BaseModel


class LearningState(BaseModel):
    last_state: str | None = None
    last_action: str | None = None
    last_needs: tuple[float, float, float, float] | None = None
