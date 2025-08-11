# llm_analysis_tools.py
import json
import logging
from typing import Any

import llm
from pydantic import BaseModel, Field

from src.constants import (
    DEFAULT_LLM_FALLBACK_MODEL,
    DEFAULT_LLM_MODEL,
    MAX_COMPANY_DESCRIPTION_WORDS,
    MAX_CONTENT_PREVIEW_CHARS,
    MAX_IMPACT_RATIONALE_WORDS,
    MAX_PROMPT_CHAR_LIMIT,
    MAX_SUMMARY_WORDS,
    MAX_TEXT_BLOCKS_FOR_ONELINER,
)
from src.error_handlers import ErrorContext, log_exceptions
from src.exceptions import LLMModelUnavailableError, LLMResponseParsingError
from src.processors.base_processor import StructuredDocumentData

# LLM config
from .config import LLM_API_KEY, LLM_FALLBACK_MODEL, LLM_MODEL

logger = logging.getLogger(__name__)


# Pydantic Schemas for Structured Output
class OneLineSummary(BaseModel):
    """Concise one-line summary of the key event or data point in the disclosure."""

    company_name_en: str = Field(..., description="Company name in English.")
    summary: str = Field(
        ...,
        description=f"Ultra concise (<{MAX_SUMMARY_WORDS} words) explanation of the key event or data point, focusing on what was decided or done.",
    )


class ExecutiveSummary(BaseModel):
    """Insightful, concise executive summary and key highlights."""

    company_name_en: str = Field(..., description="Company name in English (all caps).")
    company_description_short: str | None = Field(
        None,
        description=f"Very concise (<{MAX_COMPANY_DESCRIPTION_WORDS} words) summary of what the company does.",
    )
    summary: str = Field(
        ...,
        description="Insightful and concise executive summary interpreting the data with a strategic lens.",
    )
    key_highlights: list[str] = Field(
        ...,
        description="Key takeaways or important points from the disclosure as bullet points.",
    )
    potential_impact_rationale: str | None = Field(
        None,
        description=f"Very concise (<{MAX_IMPACT_RATIONALE_WORDS} words) summary of the potential impact, with rationale.",
    )


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
        self, structured_data: StructuredDocumentData
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


# Specific Tools


class OneLinerTool(BasePromptTool[OneLineSummary]):
    schema_class: type[OneLineSummary] = OneLineSummary
    tool_name: str = "one_line_summary"

    def _build_prompt_header(self, structured_data: StructuredDocumentData) -> str:
        """Build the header section of the prompt."""
        company_name_en = structured_data.get(
            "company_name_en", structured_data.get("company_name_ja", "Unknown Company")
        )
        document_type = structured_data.get("document_type", "document")
        document_title = structured_data.get("document_title", "")

        return (
            f"summary of the following Japanese financial disclosure text. "
            f"Focus *only* on what was decided, announced, or disclosed by the business - not the filing details or metadata. "
            f"Do not reply in Japanese."
            f"\n\nCompany Name: {company_name_en}"
            f"\nDocument Type: {document_type}"
            f"\nDocument Title: {document_title}\n\n"
            f"Disclosure Content (extracted key facts and text blocks):\n"
        )

    def _add_text_blocks_to_prompt(
        self,
        prompt: str,
        structured_data: StructuredDocumentData,
        max_blocks: int = MAX_TEXT_BLOCKS_FOR_ONELINER,
    ) -> str:
        """Add text blocks section to prompt."""
        if not structured_data.get("text_blocks"):
            return prompt

        prompt += "Relevant Text Blocks:\n"
        for block in structured_data["text_blocks"][:max_blocks]:
            content = block.get("content_jp", block.get("content", ""))
            if content:
                title = block.get("title_en", block.get("title", "Section"))
                prompt += (
                    f"--- {title} ---\n{content[:MAX_CONTENT_PREVIEW_CHARS]}...\n\n"
                )
        return prompt

    def create_prompt(self, structured_data: StructuredDocumentData) -> str:
        """Prompt for a one-line summary."""
        prompt = self._build_prompt_header(structured_data)
        prompt = self._add_key_facts_to_prompt(prompt, structured_data)
        prompt = self._add_text_blocks_to_prompt(prompt, structured_data)
        return prompt

    def format_to_text(self, schema_object: OneLineSummary) -> str:
        """Format the one-liner summary."""
        return f"{schema_object.summary}"


class ExecutiveSummaryTool(BasePromptTool[ExecutiveSummary]):
    schema_class: type[ExecutiveSummary] = ExecutiveSummary
    tool_name: str = "executive_summary"

    def _build_executive_prompt_header(
        self, structured_data: StructuredDocumentData
    ) -> str:
        """Build the header section for executive summary prompt."""
        company_name_en = structured_data.get(
            "company_name_en", structured_data.get("company_name_ja", "Unknown Company")
        )
        document_type = structured_data.get("document_type", "document")
        document_title = structured_data.get("document_title", "")

        return (
            f"\n\nProvide an insightful, concise executive summary and key highlights "
            f"of the following Japanese financial disclosure text. "
            f"Do not reply in Japanese. "
            f"Be more concise than normal and interpret the data with a strategic lens and rationale. "
            f"Provide a very concise (<{MAX_COMPANY_DESCRIPTION_WORDS} words) summary of what the company does."
            f"\n\nCompany Name: {company_name_en}"
            f"\nDocument Type: {document_type}"
            f"\nDocument Title: {document_title}\n\n"
            f"Disclosure Content (extracted key facts and text blocks):\n"
        )

    def _add_text_blocks_with_limit(
        self, prompt: str, structured_data: StructuredDocumentData
    ) -> str:
        """Add text blocks to prompt with character limit."""
        if not structured_data.get("text_blocks"):
            return prompt

        prompt += "Relevant Text Blocks:\n"
        combined_text = ""

        for block in structured_data["text_blocks"]:
            title = block.get("title_en", block.get("title", "Section"))
            content = block.get("content_jp", block.get("content", ""))
            if content:
                block_text = f"--- {title} ---\n{content}\n\n"
                # Estimate token usage - simple char count approximation
                if len(combined_text) + len(block_text) < MAX_PROMPT_CHAR_LIMIT:
                    combined_text += block_text
                else:
                    break  # Stop adding blocks if prompt gets too long

        prompt += combined_text
        return prompt

    def create_prompt(self, structured_data: StructuredDocumentData) -> str:
        """Prompt for an executive summary."""
        prompt = self._build_executive_prompt_header(structured_data)
        prompt = self._add_key_facts_to_prompt(prompt, structured_data)
        prompt = self._add_text_blocks_with_limit(prompt, structured_data)
        return prompt

    def format_to_text(self, schema_object: ExecutiveSummary) -> str:
        """Format the executive summary."""
        text = ""
        if schema_object.company_description_short:
            # Format company description separately
            text += (
                f"Company Description: {schema_object.company_description_short}\n\n"
            )
        text += f"Executive Summary: {schema_object.summary}\n\n"
        if schema_object.key_highlights:
            text += "Key Highlights:\n"
            for highlight in schema_object.key_highlights:
                text += f"- {highlight}\n"
            text += "\n"
        if schema_object.potential_impact_rationale:
            # Format potential impact separately
            text += f"Potential Impact: {schema_object.potential_impact_rationale}\n"

        return text


# Tool Map and Analysis Function
TOOL_MAP: dict[str, type[BasePromptTool[Any]]] = {
    OneLinerTool.tool_name: OneLinerTool,
    ExecutiveSummaryTool.tool_name: ExecutiveSummaryTool,
    # Add other tools here
}


def analyze_document_data(
    structured_data: StructuredDocumentData, tool_name: str
) -> str | None:
    """
    Analyze structured document data using the specified LLM tool.

    Args:
        structured_data: Structured dictionary of the document's data.
        tool_name: Name of the tool to use (key in TOOL_MAP).

    Returns:
        Formatted string output from the tool, or None if analysis failed.
    """
    if tool_name not in TOOL_MAP:
        logger.error(f"Unknown LLM analysis tool: {tool_name}")
        return f"Error: Unknown analysis tool '{tool_name}'"

    tool_class = TOOL_MAP[tool_name]
    tool_instance = tool_class()  # Create an instance of the tool

    logger.info(
        f"Attempting to generate '{tool_name}' analysis for doc_id: {structured_data.get('doc_id', 'N/A')}"
    )
    formatted_output = tool_instance.generate_formatted_text(structured_data)

    if formatted_output:
        logger.info(f"Successfully generated '{tool_name}' analysis.")
        return formatted_output
    else:
        logger.error(f"Failed to generate '{tool_name}' analysis.")
        return f"Analysis Failed for '{tool_name}'"
