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
        config_path: str,
        output_dir: str,
        type: str,
        sub_type: str,
    ):
        super().__init__(type, sub_type)
        
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.jinja_env.filters['realpath'] = lambda x: os.path.abspath(x)
        self.jinja_env.filters['is_dict']  = lambda x: isinstance(x, dict)
        self.jinja_env.trim_blocks   = True
        self.jinja_env.lstrip_blocks = True
        
    def is_tester(self):
        return True
    
    