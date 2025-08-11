# executive_summary_tool.py
import logging

from src.constants import (
    MAX_COMPANY_DESCRIPTION_WORDS,
    MAX_PROMPT_CHAR_LIMIT,
)
from src.llm_analysis.base_tool import BasePromptTool
from src.llm_analysis.schemas import ExecutiveSummary
from src.processors.base_processor import StructuredDocumentData

logger = logging.getLogger(__name__)


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
