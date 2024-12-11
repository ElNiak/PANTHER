from hypothesis import given, strategies as st
from panther.config.config_manager import validate_config

@given(
    name=st.text(min_size=1, max_size=50),
    timeout=st.integers(min_value=0, max_value=3600)
)
def test_validate_config_property(name, timeout):
    config = {"name": name, "timeout": timeout}
    assert validate_config(config) == True
