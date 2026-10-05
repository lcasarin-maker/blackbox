"""Behavior and fail-closed boundaries for the captured JSON Schema subset."""
from __future__ import annotations

import pytest

from tools.json_schema_subset import (
    UnsupportedJsonSchema,
    _matches_type,
    schema_value_matches,
)


@pytest.mark.parametrize(
    ("schema", "value"),
    [
        ({"type": "string"}, "text"),
        ({"type": "string", "enum": ["text"]}, "text"),
        ({"type": "boolean"}, False),
        ({"type": "integer"}, 3),
        ({"type": "number"}, 2.5),
        ({"type": "object"}, {"extra": "accepted by the default additionalProperties"}),
        ({"type": "array"}, []),
        ({"type": "null"}, None),
        ({"type": "number", "enum": [1]}, 1.0),
        (
            {"type": "object", "enum": [{"nested": [1, {"ok": True}]}]},
            {"nested": [1.0, {"ok": True}]},
        ),
        (
            {
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
                "additionalProperties": False,
            },
            {"enabled": True},
        ),
    ],
)
def test_supported_schema_types_accept_matching_values(schema, value) -> None:
    assert schema_value_matches(schema, value)


@pytest.mark.parametrize(
    ("schema", "value"),
    [
        ({"type": "boolean"}, 1),
        ({"type": "integer"}, True),
        ({"type": "number"}, True),
        ({"type": "number"}, float("nan")),
        ({"type": "array"}, {}),
        ({"type": "null"}, "null"),
        ({"type": "integer", "enum": [True]}, 1),
        ({"type": "boolean", "enum": [1]}, True),
        (
            {"type": "object", "enum": [{"value": True}]},
            {"value": 1},
        ),
        (
            {
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
                "additionalProperties": False,
            },
            {"enabled": "true"},
        ),
        (
            {
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
                "additionalProperties": False,
            },
            {"enabled": True, "other": 1},
        ),
        (
            {
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
                "additionalProperties": False,
            },
            {},
        ),
    ],
)
def test_supported_schema_types_reject_mismatched_values(schema, value) -> None:
    assert not schema_value_matches(schema, value)


@pytest.mark.parametrize(
    ("schema", "value", "message"),
    [
        ([], {}, "node must be an object"),
        ({"minimum": 1, "type": "number"}, 2, "unsupported keyword"),
        ({"type": "unknown"}, "value", "unsupported or absent JSON Schema type"),
        ({"type": "string", "enum": "text"}, "text", "enum must be"),
        ({"type": "string", "enum": []}, "text", "enum must be nonempty"),
        ({"type": "integer", "enum": [1, 1.0]}, 1, "enum must be nonempty"),
        ({"type": "string", "enum": ["other"]}, "text", None),
        ({"type": "string", "properties": {}}, "text", "object-only"),
        ({"type": "object", "properties": []}, {}, "malformed JSON Schema"),
        ({"type": "object", "required": [1]}, {}, "malformed JSON Schema"),
        ({"type": "object", "additionalProperties": 1}, {}, "malformed JSON Schema"),
        (
            {"type": "object", "properties": {"x": 1}},
            {"x": 1},
            "malformed JSON Schema",
        ),
        (
            {"type": "object", "properties": {}, "required": ["x"]},
            {},
            "required key lacks a property schema",
        ),
    ],
)
def test_unsupported_or_malformed_schema_never_silently_matches(schema, value, message):
    if message is None:
        assert not schema_value_matches(schema, value)
        return
    with pytest.raises(UnsupportedJsonSchema, match=message):
        schema_value_matches(schema, value)


def test_internal_type_matcher_fails_closed_for_unvalidated_kind() -> None:
    with pytest.raises(UnsupportedJsonSchema, match="unsupported or absent"):
        _matches_type("date", "2026-10-04")


@pytest.mark.parametrize(
    ("schema", "value", "matches"),
    [
        ({"type": "number", "enum": ["1"]}, 1, False),
        (
            {"type": "object", "enum": [{"first": 1, "second": [True, 2]}]},
            {"second": [True, 2.0], "first": 1.0},
            True,
        ),
        (
            {"type": "array", "enum": [[1, 2]]},
            [2, 1],
            False,
        ),
    ],
)
def test_enum_uses_json_numeric_object_and_array_equality(schema, value, matches):
    assert schema_value_matches(schema, value) is matches


def test_enum_rejects_non_json_nested_values() -> None:
    with pytest.raises(UnsupportedJsonSchema, match="enum must be nonempty"):
        schema_value_matches({"type": "array", "enum": [(1, 2)]}, [1, 2])
