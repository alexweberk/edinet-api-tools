# document_processors.py
import logging

from src.processors.base_processor import BaseDocumentProcessor, StructuredDocumentData

logger = logging.getLogger(__name__)


class SemiAnnualReportProcessor(BaseDocumentProcessor):
    """Processor for Semi-Annual Reports (doc_type_code '160')."""

    def process(self) -> StructuredDocumentData | None:
        """Extract key data points, tables, and text blocks for Semi-Annual Reports."""
        logger.debug(f"Processing Semi-Annual Report (doc_id: {self.doc_id})")
        structured_data = self._get_common_metadata()

        # --- Extract Key Financial Metrics (as key_facts) ---
        key_metrics_map = {
            "jpcrp_cor:OperatingRevenue1SummaryOfBusinessResults": "OperatingRevenue",  # 営業収益
            "jpcrp_cor:OrdinaryIncome": "OrdinaryIncome",  # 経常利益
            "jppfs_cor:ProfitLossAttributableToOwnersOfParent": "NetIncome",  # 親会社株主に帰属する当期純利益
            "jpcrp_cor:BasicEarningsLossPerShareSummaryOfBusinessResults": "EPS",  # 1株当たり当期純利益
            "jpcrp_cor:NetAssetsSummaryOfBusinessResults": "NetAssets",  # 純資産額
            "jpcrp_cor:TotalAssetsSummaryOfBusinessResults": "TotalAssets",  # 総資産額
            "jpcrp_cor:CashAndCashEquivalentsSummaryOfBusinessResults": "CashAndCashEquivalents",  # 現金及び現金同等物
        }
        key_facts = {}
        for xbrl_id, fact_key in key_metrics_map.items():
            current_value = self.get_value_by_id(
                xbrl_id, context_filter="Current"
            )  # Look for Current* contexts
            prior_value = self.get_value_by_id(
                xbrl_id, context_filter="Prior"
            )  # Look for Prior* contexts

            if current_value is not None or prior_value is not None:
                key_facts[fact_key] = {
                    "current": current_value,
                    "prior": prior_value,
                    # Could add simple % change calculation here
                }
        structured_data["key_facts"] = key_facts

        # --- Extract Key Tables (e.g., Financial Statements) ---
        financial_tables_map = {
            "jpigp_cor:CondensedQuarterlyConsolidatedStatementOfFinancialPositionIFRSTextBlock": "Consolidated Statement of Financial Position",
            "jpigp_cor:CondensedYearToQuarterEndConsolidatedStatementOfProfitOrLossIFRSTextBlock": "Consolidated Statement of Profit or Loss",
            # Add more table IDs as identified from Semi-Annual reports
        }
        structured_data["financial_tables"] = []
        for xbrl_id, table_title_en in financial_tables_map.items():
            # Find the specific text block containing the table data (often rendered as text)
            table_text_block = self.get_value_by_id(xbrl_id)
            if table_text_block:
                structured_data["financial_tables"].append(
                    {"title_en": table_title_en, "raw_text_content": table_text_block}
                )

        # --- Extract Key Text Blocks (Commentary) ---
        # Define a list of important text block IDs and their English titles
        text_block_elements = [
            ("jpcrp_cor:BusinessResultsOfGroupTextBlock", "Group Business Results"),
            ("jpcrp_cor:DescriptionOfBusinessTextBlock", "Description of Business"),
            ("jpcrp_cor:BusinessRisksTextBlock", "Business Risks"),
            (
                "jpcrp_cor:ManagementAnalysisOfFinancialPositionOperatingResultsAndCashFlowsTextBlock",
                "Management Analysis",
            ),
            ("jpcrp_cor:MajorShareholdersTextBlock", "Major Shareholders"),
            (
                "jpigp_cor:NotesSegmentInformationCondensedQuarterlyConsolidatedFinancialStatementsIFRSTextBlock",
                "Segment Information Notes",
            ),
            # Add more key text block IDs relevant to semi-annual reports
        ]
        structured_data["text_blocks"] = []
        for xbrl_id, title_en in text_block_elements:
            content = self.get_value_by_id(xbrl_id)  # Get the raw text content
            if content:
                structured_data["text_blocks"].append(
                    {
                        "id": xbrl_id,
                        "title_en": title_en,
                        "content_jp": content,  # Keep Japanese content for LLM translation
                    }
                )
        # Fallback to include all text blocks if specific ones aren't found (less structured)
        if not structured_data["text_blocks"]:
            logger.warning(
                f"Specific text blocks not found for {self.doc_id}, including all text blocks."
            )
            structured_data["text_blocks"] = self.get_all_text_blocks()

        logger.debug(
            f"Finished processing Semi-Annual Report {self.doc_id}. Extracted {len(key_facts)} key facts, {len(structured_data['financial_tables'])} financial tables, and {len(structured_data['text_blocks'])} text blocks."
        )
        return structured_data if structured_data else None
