"""DataForge ELT shared infrastructure layer.

Public API exported from this package:
- Logging: get_logger, configure_logging, pipeline_context
- Retry: RetryPolicy, build_retry_decorator, network_retry, storage_retry
- Exceptions: DataForgeError and all subclasses
- Notifications: Notifier, ConsoleNotifier, DiscordNotifier, SlackNotifier,
                 EmailNotifier, MultiNotifier, NotifierFactory,
                 NotificationLevel, NotificationPayload
- Metrics: PipelineMetrics, PipelineMetricsCollector
- Utilities: ensure_directory, utc_now, timestamp_str, slugify,
             safe_cast, flatten_dict, chunk_list, parse_size, truncate_string
"""

from shared.exceptions import (
    APIError,
    ConfigError,
    CrawlError,
    DataForgeError,
    DownloadError,
    NotificationError,
    ParseError,
    PipelineError,
    RateLimitError,
    RobotsError,
    StorageError,
    TransformError,
    ValidationError,
    WarehouseError,
)
from shared.logger import configure_logging, get_logger, pipeline_context
from shared.metrics import PipelineMetrics, PipelineMetricsCollector
from shared.notifier import (
    ConsoleNotifier,
    DiscordNotifier,
    EmailNotifier,
    MultiNotifier,
    NotificationLevel,
    NotificationPayload,
    Notifier,
    NotifierFactory,
    SlackNotifier,
)
from shared.retry import (
    DEFAULT_RETRY_POLICY,
    RetryPolicy,
    build_retry_decorator,
    network_retry,
    storage_retry,
)
from shared.utils import (
    chunk_list,
    ensure_directory,
    flatten_dict,
    parse_size,
    safe_cast,
    slugify,
    timestamp_str,
    truncate_string,
    utc_now,
)

__all__ = [
    # Logging
    "get_logger",
    "configure_logging",
    "pipeline_context",
    # Retry
    "RetryPolicy",
    "build_retry_decorator",
    "DEFAULT_RETRY_POLICY",
    "network_retry",
    "storage_retry",
    # Exceptions
    "DataForgeError",
    "ConfigError",
    "CrawlError",
    "ParseError",
    "RateLimitError",
    "RobotsError",
    "DownloadError",
    "ValidationError",
    "StorageError",
    "WarehouseError",
    "TransformError",
    "PipelineError",
    "NotificationError",
    "APIError",
    # Notifications
    "Notifier",
    "NotificationLevel",
    "NotificationPayload",
    "ConsoleNotifier",
    "DiscordNotifier",
    "SlackNotifier",
    "EmailNotifier",
    "MultiNotifier",
    "NotifierFactory",
    # Metrics
    "PipelineMetrics",
    "PipelineMetricsCollector",
    # Utilities
    "ensure_directory",
    "utc_now",
    "timestamp_str",
    "slugify",
    "safe_cast",
    "flatten_dict",
    "chunk_list",
    "parse_size",
    "truncate_string",
]
