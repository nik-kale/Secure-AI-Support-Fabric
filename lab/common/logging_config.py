"""
Structured logging configuration for AI Support Fabric Lab

Provides consistent, production-ready logging across all services
"""
import logging
import sys
import os
import json
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON

        Args:
            record: Log record

        Returns:
            JSON string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter"""

    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def setup_logging(
    service_name: str,
    level: str = None,
    log_format: str = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup structured logging for a service

    Args:
        service_name: Name of the service (e.g., 'telemetry_collector')
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        log_file: Optional path to log file

    Returns:
        Configured logger instance
    """
    # Get configuration from environment or use defaults
    level = level or os.getenv('LOG_LEVEL', 'INFO')
    log_format = log_format or os.getenv('LOG_FORMAT', 'json')

    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.propagate = False  # Prevent duplicate logs

    # Clear existing handlers
    logger.handlers.clear()

    # Choose formatter
    if log_format.lower() == 'json':
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10485760,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Failed to setup file logging: {e}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Request context logging helpers
def log_request_start(logger: logging.Logger, request_id: str, method: str, path: str):
    """Log HTTP request start"""
    logger.info(
        f"Request started: {method} {path}",
        extra={'request_id': request_id}
    )


def log_request_end(
    logger: logging.Logger,
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float
):
    """Log HTTP request completion"""
    logger.info(
        f"Request completed: {method} {path} - {status_code}",
        extra={
            'request_id': request_id,
            'status_code': status_code,
            'duration_ms': duration_ms
        }
    )


# Example usage
if __name__ == '__main__':
    # Test logging setup
    logger = setup_logging('test_service', level='DEBUG', log_format='json')

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # Test with extra fields
    logger.info(
        "Request processed successfully",
        extra={'request_id': 'req-123', 'duration_ms': 45}
    )

    # Test exception logging
    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.exception("An error occurred")

    print("\n--- Text format ---\n")

    # Test text format
    logger_text = setup_logging('test_service_text', level='INFO', log_format='text')
    logger_text.info("This is text format logging")
    logger_text.error("Error in text format")
