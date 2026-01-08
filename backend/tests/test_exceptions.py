"""Tests for custom exception hierarchy."""

import pytest

from src.exceptions import (
    CacheConnectionError,
    CacheError,
    CacheOperationError,
    ConfigurationError,
    JiraAPIError,
    JiraAuthenticationError,
    JiraFeedbackError,
    JiraNotFoundError,
    JiraPermissionError,
    JiraRateLimitError,
    LLMError,
    MissingCredentialsError,
    PipelineError,
    RubricError,
    ScoreValidationError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_base_exception(self):
        """Test base JiraFeedbackError."""
        exc = JiraFeedbackError("Base error")
        assert str(exc) == "Base error"
        assert isinstance(exc, Exception)

    def test_configuration_error_inherits_from_base(self):
        """Test ConfigurationError inherits from JiraFeedbackError."""
        exc = ConfigurationError("Config error")
        assert isinstance(exc, JiraFeedbackError)
        assert isinstance(exc, Exception)

    def test_missing_credentials_inherits_from_config(self):
        """Test MissingCredentialsError inherits from ConfigurationError."""
        exc = MissingCredentialsError("No credentials")
        assert isinstance(exc, ConfigurationError)
        assert isinstance(exc, JiraFeedbackError)

    def test_cache_error_hierarchy(self):
        """Test cache error hierarchy."""
        cache_err = CacheError("Cache error")
        conn_err = CacheConnectionError("Connection failed")
        op_err = CacheOperationError("Operation failed")

        assert isinstance(cache_err, JiraFeedbackError)
        assert isinstance(conn_err, CacheError)
        assert isinstance(op_err, CacheError)

    def test_pipeline_error_hierarchy(self):
        """Test pipeline error hierarchy."""
        pipeline_err = PipelineError("Pipeline failed")
        llm_err = LLMError("LLM failed")
        rubric_err = RubricError("Rubric failed")

        assert isinstance(pipeline_err, JiraFeedbackError)
        assert isinstance(llm_err, PipelineError)
        assert isinstance(rubric_err, PipelineError)

    def test_validation_error_hierarchy(self):
        """Test validation error hierarchy."""
        val_err = ValidationError("Invalid data")
        score_err = ScoreValidationError("Score out of range")

        assert isinstance(val_err, JiraFeedbackError)
        assert isinstance(score_err, ValidationError)


class TestJiraAPIError:
    """Test JiraAPIError with attributes."""

    def test_basic_api_error(self):
        """Test basic JiraAPIError."""
        exc = JiraAPIError("API failed")
        assert str(exc) == "API failed"
        assert exc.status_code is None
        assert exc.issue_key is None

    def test_api_error_with_status(self):
        """Test JiraAPIError with status code."""
        exc = JiraAPIError("API failed", status_code=500)
        assert exc.status_code == 500
        assert exc.issue_key is None

    def test_api_error_with_all_attributes(self):
        """Test JiraAPIError with all attributes."""
        exc = JiraAPIError("API failed", status_code=404, issue_key="TEST-123")
        assert exc.status_code == 404
        assert exc.issue_key == "TEST-123"


class TestJiraAuthenticationError:
    """Test JiraAuthenticationError."""

    def test_default_message(self):
        """Test default authentication error message."""
        exc = JiraAuthenticationError()
        assert "authentication failed" in str(exc).lower()
        assert exc.status_code == 401

    def test_custom_message(self):
        """Test custom authentication error message."""
        exc = JiraAuthenticationError("Invalid token")
        assert str(exc) == "Invalid token"
        assert exc.status_code == 401


class TestJiraRateLimitError:
    """Test JiraRateLimitError."""

    def test_default_message(self):
        """Test default rate limit error message."""
        exc = JiraRateLimitError()
        assert "rate limit" in str(exc).lower()
        assert exc.status_code == 429
        assert exc.retry_after is None

    def test_with_retry_after(self):
        """Test rate limit error with retry after."""
        exc = JiraRateLimitError(retry_after=30)
        assert exc.status_code == 429
        assert exc.retry_after == 30

    def test_custom_message_and_retry(self):
        """Test rate limit with custom message."""
        exc = JiraRateLimitError("Too many requests", retry_after=60)
        assert str(exc) == "Too many requests"
        assert exc.retry_after == 60


class TestJiraNotFoundError:
    """Test JiraNotFoundError."""

    def test_default_message(self):
        """Test default not found error message."""
        exc = JiraNotFoundError()
        assert "not found" in str(exc).lower()
        assert exc.status_code == 404
        assert exc.issue_key is None

    def test_with_issue_key(self):
        """Test not found error with issue key."""
        exc = JiraNotFoundError(issue_key="TEST-999")
        assert exc.status_code == 404
        assert exc.issue_key == "TEST-999"

    def test_custom_message(self):
        """Test not found with custom message."""
        exc = JiraNotFoundError("Issue TEST-123 does not exist", issue_key="TEST-123")
        assert str(exc) == "Issue TEST-123 does not exist"
        assert exc.issue_key == "TEST-123"


class TestJiraPermissionError:
    """Test JiraPermissionError."""

    def test_default_message(self):
        """Test default permission error message."""
        exc = JiraPermissionError()
        assert "permission denied" in str(exc).lower()
        assert exc.status_code == 403

    def test_custom_message(self):
        """Test custom permission error message."""
        exc = JiraPermissionError("Cannot access project")
        assert str(exc) == "Cannot access project"
        assert exc.status_code == 403


class TestExceptionCatching:
    """Test exception catching patterns."""

    def test_catch_all_jira_errors(self):
        """Test catching all Jira errors with base class."""
        exceptions = [
            JiraAPIError("API"),
            JiraAuthenticationError(),
            JiraRateLimitError(),
            JiraNotFoundError(),
            JiraPermissionError(),
        ]

        for exc in exceptions:
            try:
                raise exc
            except JiraAPIError as caught:
                assert caught is exc
            except Exception:
                pytest.fail(f"Expected JiraAPIError, got different exception for {type(exc)}")

    def test_catch_all_app_errors(self):
        """Test catching all app errors with base class."""
        exceptions = [
            ConfigurationError("config"),
            CacheError("cache"),
            PipelineError("pipeline"),
            ValidationError("validation"),
            JiraAPIError("api"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except JiraFeedbackError as caught:
                assert caught is exc
            except Exception:
                pytest.fail(f"Expected JiraFeedbackError, got different exception for {type(exc)}")

    def test_specific_catch_before_general(self):
        """Test specific exception caught before general."""
        exc = JiraAuthenticationError("Bad token")

        caught_type = None
        try:
            raise exc
        except JiraAuthenticationError:
            caught_type = "auth"
        except JiraAPIError:
            caught_type = "api"
        except JiraFeedbackError:
            caught_type = "base"

        assert caught_type == "auth"


class TestExceptionRaising:
    """Test exception raising patterns."""

    def test_raise_from_http_error(self):
        """Test raising Jira error from HTTP error."""
        original_error = ValueError("HTTP 401")

        try:
            try:
                raise original_error
            except ValueError as e:
                raise JiraAuthenticationError("Authentication failed") from e
        except JiraAuthenticationError as exc:
            assert exc.__cause__ is original_error

    def test_exception_chaining(self):
        """Test exception chaining works."""
        try:
            try:
                raise ConnectionError("Network down")
            except ConnectionError as e:
                raise CacheConnectionError("Cannot connect to cache") from e
        except CacheConnectionError as exc:
            assert isinstance(exc.__cause__, ConnectionError)
            assert "Network down" in str(exc.__cause__)
