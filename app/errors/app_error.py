# =============================================================================
# app/errors/app_error.py  —  CUSTOM EXCEPTION CLASS
# =============================================================================
# Python lets you create your own exception types by subclassing `Exception`.
# `AppError` carries two pieces of information:
#   1. `message`     – a human-readable description shown to the API client.
#   2. `status_code` – the HTTP status code (e.g. 404, 401, 403, 409).
#
# LEARNING CONCEPT ► Custom Exceptions
#   Python's built-in exceptions (ValueError, KeyError, etc.) are great for
#   programming bugs, but for user-facing API errors we want to control:
#     • WHAT message the user sees  ("Email already registered")
#     • WHICH HTTP status code is returned  (409 Conflict)
#
#   Custom exceptions let services say `raise AppError("...", 404)` and the
#   global handler in main.py picks it up and formats the JSON response.
#
# LEARNING EXAMPLE ► raising and catching:
#   # In a service:
#   if not user:
#       raise AppError("User not found", 404)
#
#   # In the global handler (error_handler.py):
#   async def app_error_handler(request, exc: AppError):
#       return JSONResponse(status_code=exc.status_code,
#                           content={"error": exc.message})
#
#   # This keeps route handlers clean — no try/except needed there.
# =============================================================================


class AppError(Exception):
    """
    Structured application error with an explicit HTTP status code.
    Mirrors AppError.ts — thrown by services and caught by the global
    exception handler so controllers stay clean.

    ATTRIBUTES:
        message     – what to show the client
        status_code – HTTP status code (e.g. 400, 401, 403, 404, 409, 500)

    COMMON STATUS CODES USED IN THIS PROJECT:
        400 – Bad Request        (invalid input data)
        401 – Unauthorized       (not logged in / bad token)
        403 – Forbidden          (logged in but not allowed)
        404 – Not Found          (resource doesn't exist)
        409 – Conflict           (duplicate e.g. email already in use)
        410 – Gone               (resource existed but was deleted/deactivated)
        500 – Internal Server Error (unexpected crash)
    """

    def __init__(self, message: str, status_code: int) -> None:
        # Always call the parent `Exception.__init__` with the message so
        # Python's traceback / logging system can display it.
        super().__init__(message)

        # Store our custom attributes for the error handler to read.
        self.message = message
        self.status_code = status_code
