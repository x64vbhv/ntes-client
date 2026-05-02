import json
from typing import Any

def safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text