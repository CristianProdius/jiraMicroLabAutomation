"""Custom exceptions for DSPy Jira Feedback."""


class JiraFeedbackError(Exception):
    """Base exception for all application errors."""

    pass


# Configuration Errors
class ConfigurationError(JiraFeedbackError):
    """Configuration-related errors."""

    pass


class MissingCredentialsError(ConfigurationError):
    """Missing required credentials."""

    pass


# Jira API Errors
class JiraAPIError(JiraFeedbackError):
    """Base for Jira API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        issue_key: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.issue_key = issue_key


class JiraAuthenticationError(JiraAPIError):
    """Authentication failed (401)."""

    def __init__(self, message: str = "Jira authentication failed"):
        super().__init__(message, status_code=401)


class JiraRateLimitError(JiraAPIError):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class JiraNotFoundError(JiraAPIError):
    """Resource not found (404)."""

    def __init__(self, message: str = "Resource not found", issue_key: str | None = None):
        super().__init__(message, status_code=404, issue_key=issue_key)


class JiraPermissionError(JiraAPIError):
    """Permission denied (403)."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)


# Cache Errors
class CacheError(JiraFeedbackError):
    """Cache operation errors."""

    pass


class CacheConnectionError(CacheError):
    """Failed to connect to cache database."""

    pass


class CacheOperationError(CacheError):
    """Failed cache operation."""

    pass


# Pipeline Errors
class PipelineError(JiraFeedbackError):
    """Pipeline processing errors."""

    pass


class LLMError(PipelineError):
    """LLM call failed."""

    pass


class RubricError(PipelineError):
    """Rubric evaluation failed."""

    pass


# Validation Errors
class ValidationError(JiraFeedbackError):
    """Data validation errors."""

    pass


class ScoreValidationError(ValidationError):
    """Score out of valid range."""

    pass
