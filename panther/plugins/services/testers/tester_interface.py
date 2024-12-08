from abc import ABC, abstractmethod
import os
from pathlib import Path
import socket
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

from plugins.services.services_interface import IServiceManager

class ITesterManager(IServiceManager):
    
    def __init__(
        self,
        type: str,
        protocol: str,
        implementation_name: str,
    ):
        super().__init__(type, protocol,implementation_name)
        
    
    