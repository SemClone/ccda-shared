"""
Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
All Rights Reserved.

This file is part of CCDA, a proprietary commercial software project.
Unauthorized copying, distribution, or use is strictly prohibited.
"""
import json
from typing import Any, Optional


def parse_json_field(value: Any) -> Optional[Any]:
    """
    Parse a JSONB field that may come as a string or native Python object.

    This utility handles PostgreSQL JSONB columns that may be returned as:
    - JSON strings (when fetched via some drivers)
    - Native Python dicts/lists (when properly decoded)
    - None values

    Args:
        value: The field value to parse (str, dict, list, or None)

    Returns:
        Parsed Python object (dict/list) or None if invalid/empty

    Example:
        >>> parse_json_field('{"key": "value"}')
        {'key': 'value'}
        >>> parse_json_field({'key': 'value'})
        {'key': 'value'}
        >>> parse_json_field(None)
        None
        >>> parse_json_field('invalid json')
        None
    """
    if value is None:
        return None

    # If already parsed (dict, list), return as-is
    if isinstance(value, (dict, list)):
        return value

    # If string, try to parse as JSON
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    # For other types, return as-is (shouldn't happen with JSONB)
    return value
