# error_handlers.py
"""
Standardized error handling patterns and utilities.
"""

import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from src.exceptions import EdinetRetryExceededError

T = TypeVar("T")
logger = logging.getLogger(__name__)


def retry_on_failure(
    max_retries: int = 3,
    delay_seconds: int = 5,
    exceptions: tuple = (Exception,),
    backoff_multiplier: float = 1.0,
) -> Callable:
    """
    Decorator to retry function execution on failure.

    Args:
        max_retries: Maximum number of retry attempts
        delay_seconds: Initial delay between retries in seconds
        exceptions: Tuple of exceptions to retry on
        backoff_multiplier: Multiplier for exponential backoff (1.0 = no backoff)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = delay_seconds * (backoff_multiplier**attempt)
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts. "
                            f"Final error: {e}"
                        )

            raise EdinetRetryExceededError(
                f"Function {func.__name__} failed after {max_retries} attempts"
            ) from last_exception

        return wrapper

    return decorator


def log_exceptions(
    logger_instance: logging.Logger | None = None,
    reraise: bool = True,
    return_value: Any | None = None,
) -> Callable:
    """
    Decorator to log exceptions with context.

    Args:
        logger_instance: Logger to use (defaults to module logger)
        reraise: Whether to reraise the exception after logging
        return_value: Value to return instead of reraising (only if reraise=False)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T | Any | None]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T | Any | None:
            log = logger_instance or logger
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log.error(
                    f"Exception in {func.__name__}: {e}",
                    exc_info=True,
                    extra={"function": func.__name__, "args": args, "kwargs": kwargs},
                )

                if reraise:
                    raise
                else:
                    return return_value

        return wrapper

    return decorator


def handle_api_errors[T](func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle common API errors with standardized logging.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except ConnectionError as e:
            logger.error(f"Connection error in {func.__name__}: {e}")
            raise
        except TimeoutError as e:
            logger.error(f"Timeout error in {func.__name__}: {e}")
            raise
        except ValueError as e:
            logger.error(f"Value error in {func.__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise

    return wrapper


def safe_execute(
    func: Callable[..., T],
    *args,
    default_return: T | None = None,
    log_errors: bool = True,
    **kwargs,
) -> T | None:
    """
    Safely execute a function with error handling.

    Args:
        func: Function to execute
        *args: Arguments to pass to function
        default_return: Value to return if function fails
        log_errors: Whether to log errors
        **kwargs: Keyword arguments to pass to function

    Returns:
        Function result or default_return on failure
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error executing {func.__name__}: {e}")
        return default_return


class ErrorContext:
    """Context manager for consistent error handling."""

    def __init__(
        self,
        operation_name: str,
        logger_instance: logging.Logger | None = None,
        reraise: bool = True,
        cleanup_func: Callable[..., Any] | None = None,
    ):
        self.operation_name = operation_name
        self.logger = logger_instance or logger
        self.reraise = reraise
        self.cleanup_func = cleanup_func

    def __enter__(self):
        self.logger.debug(f"Starting operation: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.logger.error(
                f"Operation '{self.operation_name}' failed: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb),
            )

            if self.cleanup_func:
                try:
                    self.cleanup_func()
                except Exception as cleanup_error:
                    self.logger.error(f"Cleanup failed: {cleanup_error}")

            if not self.reraise:
                return True  # Suppress exception
        else:
            self.logger.debug(
                f"Operation completed successfully: {self.operation_name}"
            )

        return False  # Don't suppress exception
