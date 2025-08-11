import logging

from src.constants import LOG_FORMAT


def setup_logging() -> None:
    """Configures basic logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[logging.StreamHandler()],
    )
