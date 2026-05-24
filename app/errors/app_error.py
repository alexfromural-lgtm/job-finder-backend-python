class AppError(Exception):
    """
    Structured application error with an explicit HTTP status code.
    Mirrors AppError.ts — thrown by services and caught by the global
    exception handler so controllers stay clean.
    """

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
