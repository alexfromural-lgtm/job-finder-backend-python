"""
CamelCaseJSONResponse
---------------------
A drop-in replacement for FastAPI's JSONResponse that recursively
converts every snake_case dict key in the response body to camelCase.

This keeps all service / model code in Python-idiomatic snake_case while
satisfying the React frontend that expects camelCase field names
(the same contract the original Prisma/Node backend provided).
"""

import re
import json
from typing import Any

from fastapi.responses import JSONResponse


_RE_SNAKE = re.compile(r"_([a-z])")


def _to_camel(name: str) -> str:
    """Convert a single snake_case string to camelCase."""
    return _RE_SNAKE.sub(lambda m: m.group(1).upper(), name)


def _convert(obj: Any) -> Any:
    """Recursively convert dict keys to camelCase."""
    if isinstance(obj, dict):
        return {_to_camel(k): _convert(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert(item) for item in obj]
    return obj


class CamelCaseJSONResponse(JSONResponse):
    """
    JSONResponse subclass that camelCases every key in the response body.

    Usage (set as the app-wide default):
        app = FastAPI(default_response_class=CamelCaseJSONResponse, ...)
    """

    def render(self, content: Any) -> bytes:
        return json.dumps(
            _convert(content),
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")
