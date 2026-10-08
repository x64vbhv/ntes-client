"""Small shared helpers used across the package."""

import json
from typing import Any


def safe_json_loads(text: str) -> Any:
    """Parse JSON, falling back to the raw string.

    NTES responses are usually JSON, but some endpoints return plain text
    (e.g. alert messages). Callers want the parsed structure when possible
    and the original text otherwise, so parsing failures are not fatal.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text
