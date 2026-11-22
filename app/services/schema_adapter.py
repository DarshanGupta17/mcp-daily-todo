from __future__ import annotations

from copy import deepcopy
from typing import Any


def mcp_schema_to_gemini_parameters(schema: dict[str, Any] | None) -> dict[str, Any]:
    if not schema:
        return {"type": "object", "properties": {}}

    cleaned = _sanitize_node(deepcopy(schema))
    if cleaned.get("type") != "object":
        return {"type": "object", "properties": {}}

    cleaned.pop("title", None)
    props = cleaned.get("properties") or {}
    for key in list(props.keys()):
        props[key] = _sanitize_property(props[key])

    required = cleaned.get("required")
    if isinstance(required, list):
        cleaned["required"] = [r for r in required if r in props]
    else:
        cleaned.pop("required", None)

    cleaned["properties"] = props
    return cleaned


def _sanitize_property(node: dict[str, Any]) -> dict[str, Any]:
    node = _sanitize_node(node)
    node.pop("title", None)
    node.pop("default", None)
    return node


def _sanitize_node(node: Any) -> Any:
    if not isinstance(node, dict):
        return node

    if "anyOf" in node:
        non_null = [v for v in node["anyOf"] if isinstance(v, dict) and v.get("type") != "null"]
        if len(non_null) == 1:
            merged = deepcopy(non_null[0])
            for key, value in node.items():
                if key in ("anyOf", "default"):
                    continue
                if key not in merged:
                    merged[key] = value
            return _sanitize_node(merged)
        if non_null:
            return _sanitize_node(non_null[0])

    out: dict[str, Any] = {}
    for key, value in node.items():
        if key == "anyOf":
            continue
        if key == "properties" and isinstance(value, dict):
            out[key] = {k: _sanitize_property(v) for k, v in value.items()}
        elif isinstance(value, dict):
            out[key] = _sanitize_node(value)
        elif isinstance(value, list):
            out[key] = [_sanitize_node(x) if isinstance(x, dict) else x for x in value]
        else:
            out[key] = value
    return out