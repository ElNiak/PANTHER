from abc import ABC
from typing import Any


class Event(ABC):
    def __init__(self, name: str, data: dict[str, Any] = None):
        self.name = name
        self.data = data or {}

    def __str__(self):
        return f"Event(name='{self.name}', data={self.data})"

    def __repr__(self):
        return str(self)
