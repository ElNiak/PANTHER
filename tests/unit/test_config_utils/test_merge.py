"""Tests for pure-dict merge utilities."""

import pytest

from panther.config.core.utils.merge import deep_merge, dot_notation_update


class TestDeepMerge:
    def test_flat_override(self):
        assert deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_flat_union(self):
        assert deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_nested_merge(self):
        base = {"logging": {"level": "INFO", "format": "text"}}
        override = {"logging": {"level": "DEBUG"}}
        result = deep_merge(base, override)
        assert result == {"logging": {"level": "DEBUG", "format": "text"}}

    def test_nested_new_key(self):
        base = {"a": {"b": 1}}
        override = {"a": {"c": 2}}
        assert deep_merge(base, override) == {"a": {"b": 1, "c": 2}}

    def test_override_dict_with_scalar(self):
        assert deep_merge({"a": {"b": 1}}, {"a": 42}) == {"a": 42}

    def test_override_scalar_with_dict(self):
        assert deep_merge({"a": 42}, {"a": {"b": 1}}) == {"a": {"b": 1}}

    def test_empty_base(self):
        assert deep_merge({}, {"a": 1}) == {"a": 1}

    def test_empty_override(self):
        assert deep_merge({"a": 1}, {}) == {"a": 1}

    def test_list_replaced_not_merged(self):
        assert deep_merge({"a": [1, 2]}, {"a": [3]}) == {"a": [3]}

    def test_deeply_nested(self):
        base = {"a": {"b": {"c": {"d": 1}}}}
        override = {"a": {"b": {"c": {"e": 2}}}}
        assert deep_merge(base, override) == {"a": {"b": {"c": {"d": 1, "e": 2}}}}


class TestDotNotationUpdate:
    def test_top_level(self):
        d = {"a": 1}
        dot_notation_update(d, "a", 2)
        assert d == {"a": 2}

    def test_nested(self):
        d = {"a": {"b": 1}}
        dot_notation_update(d, "a.b", 2)
        assert d == {"a": {"b": 2}}

    def test_creates_intermediate_dicts(self):
        d = {}
        dot_notation_update(d, "a.b.c", 42)
        assert d == {"a": {"b": {"c": 42}}}

    def test_preserves_siblings(self):
        d = {"a": {"b": 1, "x": 9}}
        dot_notation_update(d, "a.b", 2)
        assert d == {"a": {"b": 2, "x": 9}}

    def test_overwrites_scalar_with_nested_path(self):
        d = {"a": 42}
        dot_notation_update(d, "a.b", "value")
        assert d == {"a": {"b": "value"}}
