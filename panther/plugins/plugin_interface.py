from abc import ABC, abstractmethod
import logging
import os
from pathlib import Path
import traceback
from typing import Any, Dict

import yaml

class IPlugin(ABC):
    def __init__(
        self,
        type: str,
    ):
        self.logger = logging.getLogger(__class__.__name__)

    