import logging
import os
import sys
import time
from pathlib import Path

import structlog
from pythonjsonlogger import jsonlogger

# Define log levels
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
JSON_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

# Create logs directory with absolute path
project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)

# Configure basic logging
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "app.log"),
    ],
)

# Configure JSON file handler
json_handler = logging.FileHandler(log_dir / "app.json.log")
json_formatter = jsonlogger.JsonFormatter(JSON_LOG_FORMAT, timestamp=True)
json_handler.setFormatter(json_formatter)

# Add JSON handler to root logger
root_logger = logging.getLogger()
root_logger.addHandler(json_handler)

# Structlog processors
processors = [
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
    structlog.processors.JSONRenderer(),
]

# Configure structlog
structlog.configure(
    processors=processors,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


# Create logger factory function
def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance with the given name.

    Args:
        name: The logger name, typically __name__ of the calling module

    Returns:
        A structured logger instance
    """
    return structlog.get_logger(name)


# Custom context manager for timing operations
class TimingLogger:
    """Context manager for timing operations and logging the duration."""

    def __init__(self, logger: structlog.stdlib.BoundLogger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.kwargs = kwargs
        self.start_time: float = 0.0

    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"{self.operation} started", **self.kwargs)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type is not None:
            self.logger.error(
                f"{self.operation} failed",
                exc_info=(exc_type, exc_val, exc_tb),
                duration=duration,
                **self.kwargs,
            )
        else:
            self.logger.info(
                f"{self.operation} completed", duration=duration, **self.kwargs
            )
