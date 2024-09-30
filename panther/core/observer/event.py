from abc import ABC
from typing import Dict, Any

class Event(ABC):
    def __init__(self, name: str, data: Dict[str, Any] = None):
        self.name = name
        self.data = data or {}