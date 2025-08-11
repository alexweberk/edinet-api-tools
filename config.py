# config.py
import logging
import os

from dotenv import load_dotenv

load_dotenv(".env", override=True)

EDINET_API_KEY: str | None = os.environ.get("EDINET_API_KEY")

# Unified LLM API Key - can be OpenAI, Claude, etc. depending on llm plugin
# We prioritize a generic LLM key, fall back to OpenAI if only that's set
LLM_API_KEY: str | None = os.environ.get("LLM_API_KEY") or os.environ.get(
    "OPENAI_API_KEY"
)

# Specify default LLM model names
LLM_MODEL: str = os.environ.get("LLM_MODEL", "gpt-4o")  # Default model
LLM_FALLBACK_MODEL: str = os.environ.get(
    "LLM_FALLBACK_MODEL",
    "gpt-4-turbo",  # Fallback model
)

AZURE_OPENAI_API_KEY: str | None = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT: str | None = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION: str | None = os.environ.get("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT: str | None = os.environ.get("AZURE_OPENAI_DEPLOYMENT")


# Check for required keys and log warnings if missing
if not EDINET_API_KEY:
    logging.warning("EDINET_API_KEY not set in .env file.")

if not LLM_API_KEY:
    logging.warning("LLM_API_KEY (or OPENAI_API_KEY) not set. LLM analysis disabled.")
