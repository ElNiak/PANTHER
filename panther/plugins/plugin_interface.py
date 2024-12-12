from abc import ABC
import logging


class IPlugin(ABC):
    def __init__(self):
        self.logger = logging.getLogger(__class__.__name__)
