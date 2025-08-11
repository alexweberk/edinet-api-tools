# document_processors.py
import logging
import re
from typing import Any

from src.constants import TEXT_REPLACEMENTS, XBRL_ELEMENT_IDS

logger = logging.getLogger(__name__)


def clean_text(text: str | None) -> str | None:
    """Clean and normalize text from disclosures."""
    if text is None:
        return None
    # replace full-width space with regular space
    text = text.replace(
        TEXT_REPLACEMENTS["FULL_WIDTH_SPACE"], TEXT_REPLACEMENTS["REGULAR_SPACE"]
    )
    # remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # replace specific Japanese punctuation with Western equivalents for consistency
    # return text.replace('。', '. ').replace('、', ', ')
    return text


# Define the structure of the output dictionary for document processors
# This structured_data is what will be passed to the LLM tools
StructuredDocumentData = dict[str, Any]


class BaseDocumentProcessor:
    """Base class for document specific data extraction."""

    def __init__(
        self,
        raw_csv_data: list[dict[str, Any]],
        doc_id: str,
        doc_type_code: str,
    ) -> None:
        """
        Initialize with raw data from CSV files and document metadata.

        Args:
            raw_csv_data: List of dictionaries, each containing 'filename' and 'data' (list of rows/dicts).
            doc_id: EDINET document ID.
            doc_type_code: EDINET document type code.
        """
        self.raw_csv_data = raw_csv_data
        self.doc_id = doc_id
        self.doc_type_code = doc_type_code
        # Combine all rows from all CSVs for easier querying
        self.all_records = self._combine_raw_data()

    def _combine_raw_data(self) -> list[dict[str, Any]]:
        """Combine all rows from all CSV files into a single list."""
        combined = []
        for csv_file in self.raw_csv_data:
            # Add filename source to each row for debugging/context if needed
            # for row in csv_file.get('data', []):
            #     row['_source_file'] = csv_file.get('filename')
            combined.extend(csv_file.get("data", []))
        return combined

    def get_value_by_id(
        self,
        element_id: str,
        context_filter: str | None = None,
    ) -> str | None:
        """Helper to find a value for a specific element ID, optionally filtered by context."""
        for record in self.all_records:
            if record.get("要素ID") == element_id:
                if context_filter is None or (
                    record.get("コンテキストID")
                    and context_filter in record["コンテキストID"]
                ):
                    value = record.get("値")
                    return clean_text(value)
        return None

    def get_records_by_id(self, element_id: str) -> list[dict[str, Any]]:
        """Helper to find all records for a specific element ID."""
        return [
            record for record in self.all_records if record.get("要素ID") == element_id
        ]

    def get_all_text_blocks(self) -> list[dict[str, str]]:
        """Extract all generic TextBlock elements."""
        text_blocks = []
        for record in self.all_records:
            element_id = record.get("要素ID")
            value = record.get("値")
            item_name = record.get(
                "項目名", element_id
            )  # Use 項目名 (item name) as title

            if element_id and "TextBlock" in element_id and value:
                text_blocks.append(
                    {
                        "id": element_id,
                        "title": item_name,
                        "content": value,  # Keep original value before cleaning for LLM to process
                    }
                )
            # Include report submission reason which may not have "TextBlock" in the ID
            elif (
                element_id
                and ("ReasonForFiling" in element_id or "提出理由" in item_name)
                and value
            ):
                text_blocks.append(
                    {
                        "id": element_id,
                        "title": item_name,
                        "content": value,  # Keep original value before cleaning for LLM to process
                    }
                )

        return text_blocks

    def process(self) -> StructuredDocumentData | None:
        """
        Process the raw CSV data into a structured dictionary.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement the 'process' method")

    def _get_common_metadata(self) -> dict[str, Any]:
        """Extract common metadata available in many filings."""
        metadata = {}
        id_to_key = {
            XBRL_ELEMENT_IDS["EDINET_CODE"]: "edinet_code",
            XBRL_ELEMENT_IDS["COMPANY_NAME_JA"]: "company_name_ja",
            XBRL_ELEMENT_IDS["COMPANY_NAME_EN"]: "company_name_en",
            XBRL_ELEMENT_IDS["DOCUMENT_TYPE"]: "document_type",
            XBRL_ELEMENT_IDS[
                "DOCUMENT_TITLE_COVER"
            ]: "document_title",  # Common in some reports
            XBRL_ELEMENT_IDS["DOCUMENT_TITLE"]: "document_title",  # Common in others
        }
        for key, element_id in id_to_key.items():
            value = self.get_value_by_id(key)
            if value is not None:
                metadata[element_id] = clean_text(value)

        # Add doc_id and doc_type_code from the zip filename metadata
        metadata["doc_id"] = self.doc_id
        metadata["doc_type_code"] = self.doc_type_code

        return metadata
