"""Build request payloads from a default payload plus per-test-case overrides.

Override keys use bracket notation for nested fields, the convention the
Excel sheets use:

    quantity              -> payload["quantity"]
    delivery[pincode]     -> payload["delivery"]["pincode"]
    items[0][sku]         -> payload["items"][0]["sku"]

Special values make negative tests possible from a spreadsheet cell:

    __remove__   delete the field
    __null__     send JSON null
    __empty__    send an empty string

Cell text is read as JSON when it parses (5 -> int, true -> bool, [1,2] -> list)
and as a plain string otherwise. Wrap it in quotes ("5") to force a string.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any

REMOVE = "__remove__"
NULL = "__null__"
EMPTY = "__empty__"

_TOKEN = re.compile(r"[^\[\]]+")


def parse_key(key: str) -> list:
    """'items[0][sku]' -> ['items', 0, 'sku']"""
    parts = _TOKEN.findall(key)
    if not parts:
        raise ValueError(f"Empty override key: {key!r}")
    return [int(p) if p.isdigit() else p for p in parts]


def coerce(value: Any) -> Any:
    """Turn a spreadsheet cell into the JSON value it describes."""
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text == NULL:
        return None
    if text == EMPTY:
        return ""
    try:
        return json.loads(text)
    except ValueError:
        return value


def _child(container: Any, key: Any, next_key: Any) -> Any:
    """Return container[key], creating a dict/list for it if missing."""
    if isinstance(key, int):
        if not isinstance(container, list):
            raise TypeError(f"Expected a list for index [{key}], found {type(container).__name__}")
        while len(container) <= key:
            container.append({})
        if container[key] is None:
            container[key] = [] if isinstance(next_key, int) else {}
        return container[key]
    if key not in container or container[key] is None:
        container[key] = [] if isinstance(next_key, int) else {}
    return container[key]


def apply_overrides(payload: dict, overrides: dict) -> dict:
    """Return a deep copy of `payload` with every override applied."""
    result = copy.deepcopy(payload)
    for raw_key, raw_value in overrides.items():
        path = parse_key(raw_key)
        parent = result
        for key, next_key in zip(path[:-1], path[1:]):
            parent = _child(parent, key, next_key)

        leaf = path[-1]
        if isinstance(raw_value, str) and raw_value.strip() == REMOVE:
            if isinstance(parent, dict):
                parent.pop(leaf, None)
            elif isinstance(parent, list) and isinstance(leaf, int) and leaf < len(parent):
                parent.pop(leaf)
            continue

        value = coerce(raw_value)
        if isinstance(leaf, int):
            _child(parent, leaf, None)  # grow the list if needed
        parent[leaf] = value
    return result
