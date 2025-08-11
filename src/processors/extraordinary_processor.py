# document_processors.py
import logging

from src.constants import EXTRAORDINARY_REPORT_ELEMENT_IDS
from src.processors.base_processor import BaseDocumentProcessor, StructuredDocumentData

logger = logging.getLogger(__name__)


class ExtraordinaryReportProcessor(BaseDocumentProcessor):
    """Processor for Extraordinary Reports (doc_type_code '180')."""

    def process(self) -> StructuredDocumentData | None:
        """Extract key data points and text blocks for Extraordinary Reports."""
        logger.debug(f"Processing Extraordinary Report (doc_id: {self.doc_id})")
        structured_data = self._get_common_metadata()

        # Extract specific facts often found in Extraordinary Reports
        key_facts = {}
        # Look for elements related to decisions, resolutions, changes, M&A
        for element_id in EXTRAORDINARY_REPORT_ELEMENT_IDS:
            value = self.get_value_by_id(element_id)
            if value is not None:
                # Use a cleaner key name for the fact
                fact_key = (
                    element_id.split(":")[-1]
                    .replace("Description", "")
                    .replace("SummaryOf", "")
                    .replace("DetailsOf", "")
                    .replace("RationaleFor", "")
                    .replace("ImpactOnBusinessResults", "ImpactOnResults")
                )
                key_facts[fact_key] = value

        structured_data["key_facts"] = key_facts
        structured_data["text_blocks"] = (
            self.get_all_text_blocks()
        )  # Include all text blocks as well

        logger.debug(
            f"Finished processing Extraordinary Report {self.doc_id}."
            f"Extracted {len(key_facts)} key facts and {len(structured_data['text_blocks'])} text blocks."
        )
        return structured_data if structured_data else None
