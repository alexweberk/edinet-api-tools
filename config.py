# config.py
import logging

from dotenv import load_dotenv

from src.config_validation import (
    load_and_validate_config,
    validate_required_config,
)
from src.exceptions import ConfigurationError

load_dotenv(".env", override=True)

# Load and validate configuration
try:
    app_config = load_and_validate_config()

    # Extract validated configuration values for backward compatibility
    EDINET_API_KEY: str = app_config.edinet.api_key
    LLM_API_KEY: str | None = app_config.llm.api_key
    LLM_MODEL: str = app_config.llm.model
    LLM_FALLBACK_MODEL: str = app_config.llm.fallback_model

    # Azure configuration
    AZURE_OPENAI_API_KEY: str | None = app_config.azure.api_key
    AZURE_OPENAI_ENDPOINT: str | None = app_config.azure.endpoint
    AZURE_OPENAI_API_VERSION: str | None = app_config.azure.api_version
    AZURE_OPENAI_DEPLOYMENT: str | None = app_config.azure.deployment

    # Processing configuration
    MAX_RETRIES: int = app_config.processing.max_retries
    DELAY_SECONDS: int = app_config.processing.delay_seconds
    ANALYSIS_LIMIT: int = app_config.processing.analysis_limit
    DAYS_BACK: int = app_config.processing.days_back

    # Log any warnings for missing optional configuration
    warnings = validate_required_config(app_config)
    for warning in warnings:
        logging.warning(warning)

    logging.info("Configuration loaded and validated successfully")

except ConfigurationError as e:
    logging.error(f"Configuration error: {e}")
    raise
except Exception as e:
    logging.error(f"Unexpected error loading configuration: {e}")
    raise ConfigurationError(f"Failed to initialize configuration: {e}") from e
