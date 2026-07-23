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


@pytest.mark.unit
def test_parse_placeholders_populates_secondary_name():
    parser = PlaceholderParser()
    infos = parser.parse_placeholders("foo @{ivy_tester:ip[bgp_c]:hex} bar")
    assert len(infos) == 1
    info = infos[0]
    assert info.service == "ivy_tester"
    assert info.attribute.value == "ip"
    assert info.secondary_name == "bgp_c"
    assert info.format_type.value == "hex"


@pytest.mark.unit
def test_parse_placeholders_secondary_name_none_for_classic():
    parser = PlaceholderParser()
    infos = parser.parse_placeholders("foo @{ivy_tester:ip:hex} bar")
    assert len(infos) == 1
    assert infos[0].secondary_name is None
    assert infos[0].format_type.value == "hex"


@pytest.mark.unit
def test_find_placeholder_strings_classic():
    parser = PlaceholderParser()
    out = parser.find_placeholder_strings("foo @{ivy_tester:ip:hex} bar")
    assert out == ["@{ivy_tester:ip:hex}"]


@pytest.mark.unit
def test_find_placeholder_strings_secondary_endpoint_round_trip():
    parser = PlaceholderParser()
    out = parser.find_placeholder_strings("foo @{ivy_tester:ip[bgp_c]:hex} bar")
    assert out == ["@{ivy_tester:ip[bgp_c]:hex}"]


@pytest.mark.unit
def test_placeholder_pattern_rejects_empty_bracket():
    # Negative case: empty [] should NOT match (per the reviewer's finding)
    assert (
        PlaceholderParser.PLACEHOLDER_PATTERN.fullmatch("@{ivy_tester:ip[]:hex}")
        is None
    )
