"""DataForge ELT exception hierarchy.

All exceptions inherit from DataForgeError so callers can catch the broad
base class or handle specific sub-types as needed.
"""

from __future__ import annotations


class DataForgeError(Exception):
    """Base exception for all DataForge ELT errors.

    Args:
        message: Human-readable description of the error.
        context: Optional dict with structured metadata for logging.
    """

    def __init__(self, message: str, context: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict = context or {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(message={self.message!r}, context={self.context!r})"


class ConfigError(DataForgeError):
    """Raised for configuration or environment variable issues."""


class CrawlError(DataForgeError):
    """Raised when a web crawl operation fails.

    Args:
        message: Description of the failure.
        url: The URL that was being crawled.
        status_code: HTTP status code if available.
        context: Additional metadata.
    """

    def __init__(
        self,
        message: str,
        url: str = "",
        status_code: int | None = None,
        context: dict | None = None,
    ) -> None:
        super().__init__(message, context)
        self.url = url
        self.status_code = status_code


class ParseError(DataForgeError):
    """Raised when parsing extracted content fails.

    Args:
        message: Description of the failure.
        raw_content: The content that could not be parsed.
        context: Additional metadata.
    """

    def __init__(
        self,
        message: str,
        raw_content: str | None = None,
        context: dict | None = None,
    ) -> None:
        super().__init__(message, context)
        self.raw_content = raw_content


class RateLimitError(CrawlError):
    """Raised when a target site returns a rate-limit response.

    Args:
        message: Description of the failure.
        url: The rate-limited URL.
        retry_after: Seconds to wait before retrying.
        context: Additional metadata.
    """

    def __init__(
        self,
        message: str,
        url: str = "",
        retry_after: int = 60,
        context: dict | None = None,
    ) -> None:
        super().__init__(message, url=url, status_code=429, context=context)
        self.retry_after = retry_after


class RobotsError(CrawlError):
    """Raised when robots.txt disallows access to the requested URL."""


class DownloadError(DataForgeError):
    """Raised when a Kaggle or HTTP download fails."""


class ValidationError(DataForgeError):
    """Raised when data fails schema or business-rule validation.

    Args:
        message: Description of the failure.
        field: The field that failed validation.
        value: The invalid value.
        context: Additional metadata.
    """

    def __init__(
        self,
        message: str,
        field: str = "",
        value: object = None,
        context: dict | None = None,
    ) -> None:
        super().__init__(message, context)
        self.field = field
        self.value = value


class StorageError(DataForgeError):
    """Raised for file I/O and object storage errors."""


class WarehouseError(DataForgeError):
    """Raised for DuckDB warehouse errors."""


class TransformError(DataForgeError):
    """Raised for dbt or pipeline transformation errors."""


class PipelineError(DataForgeError):
    """Raised for orchestration-level pipeline errors.

    Args:
        message: Description of the failure.
        pipeline_id: Identifier of the failed pipeline run.
        context: Additional metadata.
    """

    def __init__(
        self,
        message: str,
        pipeline_id: str = "",
        context: dict | None = None,
    ) -> None:
        super().__init__(message, context)
        self.pipeline_id = pipeline_id


class NotificationError(DataForgeError):
    """Raised when a notification delivery attempt fails."""


class APIError(DataForgeError):
    """Raised for FastAPI layer errors.

    Args:
        message: Description of the failure.
        status_code: HTTP status code to return to the client.
        context: Additional metadata.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        context: dict | None = None,
    ) -> None:
        super().__init__(message, context)
        self.status_code = status_code
