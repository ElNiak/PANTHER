# utils/config_validator.py

from cerberus import Validator
import yaml

class ConfigValidator:
    def __init__(self, schema: dict):
        self.validator = Validator(schema)

    def validate(self, config_path: str) -> bool:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if self.validator.validate(config):
            return True
        else:
            print("Configuration validation errors:", self.validator.errors)
            return False