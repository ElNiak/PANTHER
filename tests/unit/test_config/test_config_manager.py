import pytest
from panther.config.config_manager import validate_config

def test_validate_config_valid():
    config = {"name": "experiment1", "timeout": 60}
    assert validate_config(config) == True

def test_validate_config_invalid_name():
    config = {"name": 123, "timeout": 60}
    with pytest.raises(ValueError, match="Invalid name"):
        validate_config(config)

def test_validate_config_invalid_timeout():
    config = {"name": "experiment1", "timeout": -5}
    with pytest.raises(ValueError, match="Invalid timeout"):
        validate_config(config)
