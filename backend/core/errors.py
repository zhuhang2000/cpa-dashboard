"""Expected application failures, independent of the HTTP framework."""


class ApiError(Exception):
    """Keep the existing public status/message contract for HTTP and CLI callers."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message
