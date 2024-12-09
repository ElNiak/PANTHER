import os
import logging
from pathlib import Path
from typing import Dict, Any

from core.observer.event_manager import EventManager
from plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment

class PtraceEnvironment(IExecutionEnvironment):
    def __init__(
        self,
        output_dir: str,
        environment_settings: Dict[str,Any],
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(output_dir, environment_settings, env_type, env_sub_type, event_manager)
        self.source_dir = "/opt/panther"
    
    def setup_environment(self, services: Dict[str, Dict[str, Any]]):
        raise NotImplementedError
    
    def teardown_environment(self):
        raise NotImplementedError
