from typing import Literal, NamedTuple

EventType = Literal[
    "agent_born",
    "agent_died",
    "agent_moved",
    "agent_drank",
    "agent_ate",
    "harvest_started",
    "harvest_abandoned",
    "fruit_harvested",
    "fruit_grew",
    "fruit_depleted",
    "river_tile_added",
    "river_completed",
]


class Event(NamedTuple):
    type: EventType
    data: dict
