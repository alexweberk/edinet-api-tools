# config_validation.py
"""
Configuration validation using Pydantic models.
"""

import os
from typing import Any

from pydantic import BaseModel, Field, validator

from src.exceptions import ConfigurationError


class LLMConfig(BaseModel):
    """LLM configuration validation."""

    api_key: str | None = Field(None, description="API key for LLM service")
    model: str = Field(default="gpt-4o", description="Primary LLM model")
    fallback_model: str = Field(default="gpt-4-turbo", description="Fallback LLM model")

    @validator("api_key")
    @classmethod
    def validate_api_key(cls, v: Any) -> str | None:
        """Validate API key is present."""
        if not v:
            return None  # Allow None, but will log warning
        if len(v.strip()) < 10:
            raise ValueError("API key appears to be too short")
        return v.strip()

    @validator("model", "fallback_model")
    @classmethod
    def validate_model_names(cls, v: Any) -> str:
        """Validate model names are not empty."""
        if not v or not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()


class AzureConfig(BaseModel):
    """Azure OpenAI configuration validation."""

    api_key: str | None = None
    endpoint: str | None = None
    api_version: str | None = None
    deployment: str | None = None

    @validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: Any) -> str | None:
        """Validate Azure endpoint format."""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("Azure endpoint must start with http:// or https://")
        return v

    @validator("api_version")
    @classmethod
    def validate_api_version(cls, v: Any) -> str | None:
        """Validate API version format."""
        import re

        if v and not re.match(r"^\d{4}-\d{2}-\d{2}(-preview)?$", v):
            raise ValueError(
                "API version must be in format YYYY-MM-DD or YYYY-MM-DD-preview"
            )
        return v


class EdinetConfig(BaseModel):
    """EDINET API configuration validation."""

    api_key: str = Field(..., description="EDINET API key (required)")

    @validator("api_key")
    @classmethod
    def validate_api_key(cls, v: Any) -> str:
        """Validate EDINET API key."""
        if not v:
            raise ValueError("EDINET_API_KEY is required")
        if len(v.strip()) < 10:
            raise ValueError("EDINET API key appears to be too short")
        return v.strip()


class ProcessingConfig(BaseModel):
    """Document processing configuration validation."""

    max_retries: int = Field(
        default=3, ge=1, le=10, description="Maximum retry attempts"
    )
    delay_seconds: int = Field(
        default=5, ge=1, le=60, description="Delay between retries"
    )
    analysis_limit: int = Field(
        default=5, ge=1, le=100, description="Max documents to analyze"
    )
    days_back: int = Field(default=7, ge=1, le=365, description="Days to search back")

    @validator("max_retries", "delay_seconds", "analysis_limit", "days_back")
    @classmethod
    def validate_positive(cls, v: Any) -> int:
        """Ensure values are positive."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v


class AppConfig(BaseModel):
    """Complete application configuration."""

    edinet: EdinetConfig
    llm: LLMConfig
    azure: AzureConfig = AzureConfig()
    processing: ProcessingConfig = ProcessingConfig()

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        use_enum_values = True


def load_and_validate_config() -> AppConfig:
    """
    Load configuration from environment variables and validate it.

    Returns:
        Validated AppConfig instance

    Raises:
        ConfigurationError: If configuration is invalid
    """
    try:
        # Extract environment variables
        edinet_api_key = os.environ.get("EDINET_API_KEY")

        # LLM configuration with fallbacks
        llm_api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        llm_model = os.environ.get("LLM_MODEL", "gpt-4o")
        llm_fallback_model = os.environ.get("LLM_FALLBACK_MODEL", "gpt-4-turbo")

        # Azure configuration
        azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        azure_api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
        azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

        # Processing configuration with type conversion
        max_retries = int(os.environ.get("MAX_RETRIES", "3"))
        delay_seconds = int(os.environ.get("DELAY_SECONDS", "5"))
        analysis_limit = int(os.environ.get("ANALYSIS_LIMIT", "5"))
        days_back = int(os.environ.get("DAYS_BACK", "7"))

        # Create and validate configuration
        config = AppConfig(
            edinet=EdinetConfig(api_key=edinet_api_key),
            llm=LLMConfig(
                api_key=llm_api_key, model=llm_model, fallback_model=llm_fallback_model
            ),
            azure=AzureConfig(
                api_key=azure_api_key,
                endpoint=azure_endpoint,
                api_version=azure_api_version,
                deployment=azure_deployment,
            ),
            processing=ProcessingConfig(
                max_retries=max_retries,
                delay_seconds=delay_seconds,
                analysis_limit=analysis_limit,
                days_back=days_back,
            ),
        )

        return config

    except ValueError as e:
        raise ConfigurationError(f"Invalid configuration: {e}") from e
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}") from e


def validate_required_config(config: AppConfig) -> list[str]:
    """
    Check for missing required configuration and return warnings.

    Args:
        config: Validated AppConfig instance

    Returns:
        List of warning messages for missing optional config
    """
    warnings = []

    # Check for LLM API key
    if not config.llm.api_key:
        warnings.append(
            "LLM_API_KEY (or OPENAI_API_KEY) not set. LLM analysis will be disabled."
        )

    # Check for Azure completeness
    azure_fields = [
        config.azure.api_key,
        config.azure.endpoint,
        config.azure.api_version,
        config.azure.deployment,
    ]
    if any(azure_fields) and not all(azure_fields):
        warnings.append(
            "Partial Azure OpenAI configuration detected. "
            "All Azure fields (API_KEY, ENDPOINT, API_VERSION, DEPLOYMENT) are needed."
        )

    return warnings
