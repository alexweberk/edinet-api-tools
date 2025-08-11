# base_tool.py
import json
import logging

import llm
from pydantic import BaseModel

# LLM config
from src.config import LLM_API_KEY, LLM_FALLBACK_MODEL, LLM_MODEL
from src.constants import (
    DEFAULT_LLM_FALLBACK_MODEL,
    DEFAULT_LLM_MODEL,
)
from src.error_handlers import ErrorContext, log_exceptions
from src.exceptions import LLMModelUnavailableError, LLMResponseParsingError
from src.processors.base_processor import StructuredDocumentData

logger = logging.getLogger(__name__)


# Base Tool class
class BasePromptTool[T_Schema: BaseModel]:
    """Base class for all prompt-based tools that use schemas."""

    schema_class: type[T_Schema]  # Must be defined by subclasses
    tool_name: str = "BaseTool"

    def __init__(self) -> None:
        pass

    def get_model(self) -> "llm.Model":
        """Get the appropriate LLM model based on configuration."""
        if not LLM_API_KEY:
            logger.error("LLM_API_KEY is not set. Cannot get LLM model.")
            raise LLMModelUnavailableError("LLM_API_KEY is not set.")

        # Use the llm library to get the model, passing the API key
        # This assumes the llm library handles routing the key to the correct plugin (e.g., openai)
        # If using a specific plugin, might need to configure it first,
        # or ensure llm handles env var OPENAI_API_KEY etc.
        # We rely on llm's default behavior or env vars for now.

        try:
            model = llm.get_model(LLM_MODEL or DEFAULT_LLM_MODEL)
            # llm might need the key passed explicitly depending on setup/plugin
            logger.debug(f"Using primary LLM model: {model.model_id}")
            return model
        except Exception as e:
            logger.warning(
                f"Failed to get primary LLM model '{LLM_MODEL or DEFAULT_LLM_MODEL}': {e}. Attempting fallback."
            )
            try:
                fallback_model = llm.get_model(
                    LLM_FALLBACK_MODEL or DEFAULT_LLM_FALLBACK_MODEL
                )
                logger.debug(f"Using fallback LLM model: {fallback_model.model_id}")
                return fallback_model
            except Exception as fallback_e:
                logger.error(
                    f"Failed to get fallback LLM model '{LLM_FALLBACK_MODEL or DEFAULT_LLM_FALLBACK_MODEL}': {fallback_e}. LLM analysis disabled."
                )
                raise LLMModelUnavailableError(
                    f"Failed to get any LLM model: {e}, {fallback_e}"
                ) from e

    def create_prompt(self, structured_data: StructuredDocumentData) -> str:
        """
        Create the prompt text for the LLM from structured document data.
        Subclasses must implement this based on their schema and data needs.
        """
        raise NotImplementedError("Subclasses must implement create_prompt")

    def format_to_text(self, schema_object: T_Schema) -> str:
        """
        Format the schema object output into a human-readable string.
        Subclasses must implement this.
        """
        raise NotImplementedError("Subclasses must implement format_to_text")

    def _extract_parsed_object_from_response(self, response) -> T_Schema:
        """Extract and parse the schema object from LLM response."""
        # Preferred: Access the parsed object if llm provides it directly
        if hasattr(response, "schema_object") and response.schema_object is not None:
            logger.debug("Using response.schema_object for parsing.")
            return response.schema_object
        elif hasattr(response, "parsed_data") and response.parsed_data is not None:
            logger.debug("Using response.parsed_data for parsing.")
            return response.parsed_data
        else:
            logger.debug(
                "LLM response object did not have built-in schema object. Attempting JSON parse."
            )
            return self._parse_json_response(response)

    def _parse_json_response(self, response) -> T_Schema:
        """Parse JSON response text into schema object."""
        response_text = response.text()
        if not response_text or not response_text.strip():
            raise LLMResponseParsingError("LLM returned empty or whitespace response.")

        parsed_dict = json.loads(response_text)
        return self.schema_class(**parsed_dict)

    def _generate_llm_response(self, structured_data: StructuredDocumentData):
        """Generate response from LLM model."""
        model = self.get_model()
        prompt_text = self.create_prompt(structured_data)

        return model.prompt(
            prompt_text,
            schema=self.schema_class,
            system="You are a helpful financial analyst. Follow the schema provided precisely. Respond ONLY with valid JSON that conforms to the provided schema.",
        )

    @log_exceptions(logger, reraise=False, return_value=None)
    def generate_structured_output(
        self,
        structured_data: StructuredDocumentData,
    ) -> T_Schema | None:
        """Generate structured output from document data using the schema."""
        with ErrorContext(
            f"Generating {self.tool_name} analysis", logger, reraise=False
        ):
            response = self._generate_llm_response(structured_data)

            try:
                parsed_object = self._extract_parsed_object_from_response(response)
                logger.info(
                    f"Successfully generated structured output for {self.tool_name}."
                )
                return parsed_object

            except (json.JSONDecodeError, ValueError, TypeError) as parse_error:
                logger.error(
                    f"Failed to parse LLM response into {self.schema_class.__name__} schema for tool {self.tool_name}: {parse_error}"
                )
                logger.debug(
                    f"Raw LLM response text (attempted parse): {response.text()}"
                )
                return None
            except LLMModelUnavailableError:
                logger.error(
                    f"Skipping {self.tool_name} generation due to LLM model unavailability."
                )
                return None

    def generate_formatted_text(
        self, structured_data: StructuredDocumentData
    ) -> str | None:
        """Generate structured output and format it to plain text."""
        structured_output = self.generate_structured_output(structured_data)
        if structured_output:
            try:
                return self.format_to_text(structured_output)
            except Exception as e:
                logger.error(f"Error formatting {self.tool_name} output to text: {e}")
                return f"Error formatting analysis: {e}"
        return None

    def _add_key_facts_to_prompt(
        self, prompt: str, structured_data: StructuredDocumentData
    ) -> str:
        """Add key facts section to prompt."""
        if not structured_data.get("key_facts"):
            return prompt

        prompt += "Key Facts:\n"
        for key, value in structured_data["key_facts"].items():
            if isinstance(value, dict) and "current" in value:
                prompt += f"- {key}: Current: {value.get('current', 'N/A')}, Prior: {value.get('prior', 'N/A')}\n"
            else:
                prompt += f"- {key}: {value}\n"
        prompt += "\n"
        return prompt
