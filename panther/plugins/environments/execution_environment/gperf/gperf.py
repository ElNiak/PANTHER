import os
import logging
from typing import Dict, Any
from plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment

class GPerfEnvironment(IExecutionEnvironment):
    def __init__(self):
        self.logger = logging.getLogger("GPerfEnvironment")
    
    def setup_environment(self, services: Dict[str, Dict[str, Any]]):
        raise NotImplementedError
    
    def teardown_environment(self):
        raise NotImplementedError
