import subprocess
import logging
import os
from plugins.services.implementations.implementation_interface import IImplementationManager

class PingPongServiceManager(IImplementationManager):
    def __init__(
        self,
        output_dir: str,
        type: str,
        sub_type: str,
    ):
        super().__init__(output_dir, type, sub_type)
        
    
