from pydantic import BaseModel
from typing import List, Literal


# Your models and endpoints here
class Device(BaseModel):
    id: str
    name: str
    type: str
    status: str
    command_history: List[str]


class Command(BaseModel):
    action: Literal["status"]
    value: Literal["online", "offline"]
