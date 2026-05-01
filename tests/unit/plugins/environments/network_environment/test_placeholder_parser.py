import pytest

from panther.plugins.environments.network_environment.placeholder_parser import (
    PlaceholderParser,
)


@pytest.mark.unit
def test_placeholder_pattern_classic_three_tuple():
    m = PlaceholderParser.PLACEHOLDER_PATTERN.fullmatch("@{ivy_tester:ip:hex}")
    assert m is not None
    assert m.group(1) == "ivy_tester"
    assert m.group(2) == "ip"
    # secondary_name slot empty
    assert m.group(3) is None
    assert m.group(4) == "hex"


@pytest.mark.unit
def test_placeholder_pattern_secondary_endpoint():
    m = PlaceholderParser.PLACEHOLDER_PATTERN.fullmatch("@{ivy_tester:ip[bgp_c]:hex}")
    assert m is not None
    assert m.group(1) == "ivy_tester"
    assert m.group(2) == "ip"
    assert m.group(3) == "bgp_c"
    assert m.group(4) == "hex"


@pytest.mark.unit
def test_placeholder_pattern_secondary_endpoint_no_format():
    m = PlaceholderParser.PLACEHOLDER_PATTERN.fullmatch("@{ivy_tester:ip[bgp_c]}")
    assert m is not None
    assert m.group(3) == "bgp_c"
    assert m.group(4) is None


@pytest.mark.unit
def test_placeholder_pattern_two_tuple_legacy():
    m = PlaceholderParser.PLACEHOLDER_PATTERN.fullmatch("@{ivy_tester:ip}")
    assert m is not None
    assert m.group(2) == "ip"
    assert m.group(3) is None
    assert m.group(4) is None
