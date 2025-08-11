# document_processors.py
import logging

from src.processors.base_processor import BaseDocumentProcessor, StructuredDocumentData

logger = logging.getLogger(__name__)


class GenericReportProcessor(BaseDocumentProcessor):
    """Processor for other document types (default)."""

    def process(self) -> StructuredDocumentData | None:
        """Extract common metadata and all text blocks for generic reports."""
        logger.debug(
            f"Processing Generic Report (doc_id: {self.doc_id}, type: {self.doc_type_code})"
        )
        structured_data = self._get_common_metadata()
        structured_data[
            "key_facts"
        ] = {}  # Generic reports might not have standardized facts
        structured_data["financial_tables"] = []  # Or standardized tables

        # For generic reports, primarily extract all text blocks
        structured_data["text_blocks"] = self.get_all_text_blocks()

        logger.debug(
            f"Finished processing Generic Report {self.doc_id}."
            f"Extracted {len(structured_data['text_blocks'])} text blocks."
        )
        return structured_data if structured_data else None
