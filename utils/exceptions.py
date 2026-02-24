# utils/exceptions.py

"""Custom exception hierarchy for the Pipeline Healer Agent."""


class HealingError(Exception):
    """Base exception for all pipeline healing errors."""

    def __init__(self, message: str, step: str = "unknown", details: dict | None = None):
        self.step = step
        self.details = details or {}
        super().__init__(message)

    def __str__(self):
        base = super().__str__()
        return f"[{self.step}] {base}"


class GitHubAPIError(HealingError):
    """Raised when a GitHub API call fails."""

    def __init__(self, message: str, status_code: int | None = None, **kwargs):
        self.status_code = status_code
        super().__init__(message, **kwargs)


class LLMError(HealingError):
    """Raised when the LLM call fails or returns unparseable output."""

    def __init__(self, message: str, raw_response: str | None = None, **kwargs):
        self.raw_response = raw_response
        super().__init__(message, **kwargs)


class ValidationError(HealingError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str = "", **kwargs):
        self.field = field
        super().__init__(message, **kwargs)
