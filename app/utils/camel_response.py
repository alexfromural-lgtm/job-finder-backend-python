# =============================================================================
# app/utils/camel_response.py  —  AUTOMATIC snake_case → camelCase CONVERSION
# =============================================================================
# Python convention: use snake_case for identifiers  (created_at, job_id)
# JavaScript convention: use camelCase for JSON keys (createdAt, jobId)
#
# Without this module we'd have to rename every dict key manually in every
# service and route.  Instead, we override FastAPI's JSON serialiser ONCE so
# every response is automatically camelCased.
#
# LEARNING CONCEPT ► Subclassing / Overriding
#   We inherit from FastAPI's built-in `JSONResponse` and override only the
#   `render` method (which serialises the content to bytes).  Everything else
#   (status codes, headers, cookies) stays the same.
#
#   This is the Open/Closed principle from SOLID:
#     "Open for extension, closed for modification."
#
# LEARNING CONCEPT ► Regex (regular expression)
#   `re.compile(r"_([a-z])")` pre-compiles a pattern for speed.
#   It matches an underscore followed by a lowercase letter, e.g.:
#     "created_at" → matches "_a"
#     "job_seeker_id" → matches "_s" and "_i"
#   The lambda replaces each match with the uppercase letter:
#     "_a" → "A",  so "created_at" → "createdAt"
# =============================================================================

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


# =============================================================================
# REGEX PATTERN
# =============================================================================
# `re.compile(...)` compiles the pattern once at module load time.
# Compiled patterns are faster when used repeatedly (like on every response).
#
# Pattern breakdown: r"_([a-z])"
#   _       – literal underscore character
#   ([a-z]) – capture group: any lowercase letter a-z
#
# LEARNING EXAMPLE ► manual testing:
#   _RE_SNAKE.sub(lambda m: m.group(1).upper(), "job_id")
#   → "jobId"   (underscore removed, 'i' capitalised)
# =============================================================================
_RE_SNAKE = re.compile(r"_([a-z])")


# =============================================================================
# _to_camel: convert one key string
# =============================================================================
# `_RE_SNAKE.sub(replacement, string)` replaces all matches in `string`.
# The lambda receives a match object; `m.group(1)` is the captured letter.
#
# LEARNING EXAMPLES:
#   _to_camel("created_at")     → "createdAt"
#   _to_camel("job_seeker_id")  → "jobSeekerId"
#   _to_camel("userId")         → "userId"   (no change — no underscores)
#   _to_camel("is_active")      → "isActive"
# =============================================================================
def _to_camel(name: str) -> str:
    """Convert a single snake_case string to camelCase."""
    return _RE_SNAKE.sub(lambda m: m.group(1).upper(), name)


# =============================================================================
# _convert: recursively convert all keys in a structure
# =============================================================================
# We recurse through dicts and lists because API responses are often nested:
#   {"user": {"created_at": "...", "job_seeker": {"resume_url": "..."}}}
#
# LEARNING CONCEPT ► Recursive function
#   A function that calls itself.  Here we handle three cases:
#   1. dict   → convert all keys + recursively convert values
#   2. list   → recursively convert each item
#   3. other  → return as-is (str, int, bool, None, etc.)
# =============================================================================
def _convert(obj: Any) -> Any:
    """Recursively convert dict keys to camelCase."""
    if isinstance(obj, dict):
        # dict comprehension: { new_key: new_value for each k, v in obj }
        return {_to_camel(k): _convert(v) for k, v in obj.items()}
    if isinstance(obj, list):
        # list comprehension: [new_item for each item in obj]
        return [_convert(item) for item in obj]
    return obj  # base case: not a dict or list, return unchanged


# =============================================================================
# CamelCaseJSONResponse
# =============================================================================
# `render(content)` is called by FastAPI with the dict returned from the route.
# We intercept it, run `_convert`, then serialize with json.dumps.
#
# REGISTERED IN app/main.py:
#   app = FastAPI(default_response_class=CamelCaseJSONResponse, ...)
#
# LEARNING EXAMPLE ► a route returning snake_case keys:
#   return {"created_at": "2024-01-01", "is_active": True, "job_id": "abc"}
#   → client receives: {"createdAt": "2024-01-01", "isActive": true, "jobId": "abc"}
#
# `json.dumps` options:
#   allow_nan=False    → reject Python's float('nan') / float('inf') (not valid JSON)
#   indent=None        → compact output (no extra whitespace)
#   separators=(",":") → no spaces after comma/colon (smaller payload)
# =============================================================================
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
