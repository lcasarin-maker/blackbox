"""JSON Schema subset shared by runtime-output verifiers.

Supported keywords are ``type``, ``enum``, ``properties``, ``required``, and
``additionalProperties``. Any other keyword is deliberately unsupported and
must remain UNKNOWN rather than silently weakening the contract.
"""
from __future__ import annotations

import math
from typing import Any


class UnsupportedJsonSchema(ValueError):
    """The captured schema is outside this evaluator's explicit subset."""


def _matches_type(kind: Any, value: Any) -> bool:
    if kind == "string":
        return isinstance(value, str)
    if kind == "boolean":
        return type(value) is bool
    if kind == "integer":
        return type(value) is int
    if kind == "number":
        return isinstance(value, (int, float)) and type(value) is not bool and math.isfinite(value)
    if kind == "object":
        return isinstance(value, dict)
    if kind == "array":
        return isinstance(value, list)
    if kind == "null":
        return value is None
    raise UnsupportedJsonSchema(f"unsupported or absent JSON Schema type: {kind!r}")


def schema_value_matches(schema: Any, value: Any) -> bool:
    validate_schema(schema)
    return _value_matches_validated(schema, value)


def validate_schema(schema: Any) -> None:
    if not isinstance(schema, dict):
        raise UnsupportedJsonSchema("JSON Schema node must be an object")
    supported = {"type", "enum", "properties", "required", "additionalProperties"}
    unknown = set(schema) - supported
    if unknown:
        raise UnsupportedJsonSchema(
            "unsupported keyword(s): " + ", ".join(sorted(unknown))
        )
    kind = schema.get("type")
    if kind not in {"string", "boolean", "integer", "number", "object", "array", "null"}:
        raise UnsupportedJsonSchema(f"unsupported or absent JSON Schema type: {kind!r}")
    if "enum" in schema:
        enum_values = schema["enum"]
        if (
            not isinstance(enum_values, list)
            or not enum_values
            or any(not _is_json_value(item) for item in enum_values)
            or any(
                _json_equal(enum_values[index], enum_values[prior])
                for index in range(len(enum_values))
                for prior in range(index)
            )
        ):
            raise UnsupportedJsonSchema("JSON Schema enum must be nonempty unique JSON values")
    if kind != "object":
        if any(key in schema for key in ("properties", "required", "additionalProperties")):
            raise UnsupportedJsonSchema("object-only JSON Schema keyword on non-object type")
        return
    _validate_object_schema(schema)


def _value_matches_validated(schema: dict[str, Any], value: Any) -> bool:
    kind = schema["type"]
    if not _matches_type(kind, value):
        return False
    if "enum" in schema and not any(
        _json_equal(value, enum_value) for enum_value in schema["enum"]
    ):
        return False
    if kind != "object":
        return True
    return _object_matches(schema, value)


def _validate_object_schema(schema: dict[str, Any]) -> None:
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    additional = schema.get("additionalProperties", True)
    if (
        not isinstance(properties, dict)
        or not isinstance(required, list)
        or any(not isinstance(key, str) for key in required)
        or type(additional) is not bool
        or any(not isinstance(child, dict) for child in properties.values())
    ):
        raise UnsupportedJsonSchema("malformed JSON Schema object constraints")
    if not set(required) <= properties.keys():
        raise UnsupportedJsonSchema("JSON Schema required key lacks a property schema")
    for child in properties.values():
        validate_schema(child)


def _object_matches(schema: dict[str, Any], value: dict[str, Any]) -> bool:
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    additional = schema.get("additionalProperties", True)
    assert isinstance(properties, dict)
    assert isinstance(required, list)
    assert type(additional) is bool
    if not set(required) <= value.keys():
        return False
    for key, item in value.items():
        if key not in properties:
            if additional:
                continue
            return False
        if not _value_matches_validated(properties[key], item):
            return False
    return True


def _json_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int equality collision."""
    if type(left) is bool or type(right) is bool:
        return type(left) is bool and type(right) is bool and left is right
    if type(left) in {int, float} and type(right) in {int, float}:
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return (
            left.keys() == right.keys()
            and all(_json_equal(left[key], right[key]) for key in left)
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def _is_json_value(value: Any) -> bool:
    if value is None or type(value) in {str, bool, int}:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_value(item)
            for key, item in value.items()
        )
    return False
