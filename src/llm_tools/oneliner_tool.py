# oneliner_tool.py
import logging

from src.constants import (
    MAX_CONTENT_PREVIEW_CHARS,
    MAX_TEXT_BLOCKS_FOR_ONELINER,
)
from src.llm_tools.base_tool import BasePromptTool
from src.llm_tools.schemas import OneLineSummary
from src.processors.base_processor import StructuredDocumentData

logger = logging.getLogger(__name__)


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
