import subprocess
import logging
import os
from plugins.services.iut.implementation_interface import IImplementationManager

class PingPongServiceManager(IImplementationManager):
    def __init__(
        self,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(output_dir, type, sub_type)
        
    
