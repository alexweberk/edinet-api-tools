import argparse
import json
import logging
import sys

from src.config import ANALYSIS_LIMIT, DAYS_BACK
from src.constants import DEFAULT_DOWNLOAD_DIR, SUPPORTED_DOC_TYPES
from src.edinet.edinet_tools import download_documents
from src.llm_tools import TOOL_MAP
from src.logging_config import setup_logging
from src.services import (
    analyze_document_data,
    get_most_recent_documents,
    get_structured_data_for_company_date_range,
    get_structured_data_from_zip_directory,
)
from src.utils import print_header, print_progress

setup_logging()
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="EDINET API Tools - Fetch and analyze Japanese financial disclosure documents"
    )

    # Company date range query flags
    parser.add_argument(
        "--edinet-code",
        type=str,
        help="EDINET code for the company to fetch documents for",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date for the date range (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--end-date", type=str, help="End date for the date range (YYYY-MM-DD format)"
    )
    parser.add_argument(
        "--doc-types",
        type=str,
        help="Comma-separated list of document type codes to include (e.g., 160,180)",
    )
    parser.add_argument(
        "--output", type=str, help="Optional output file path to write JSON results"
    )

    return parser.parse_args()


def run_company_date_range_query(args):
    """Run the company date range query based on CLI arguments."""
    # Parse doc types if provided
    doc_type_codes = None
    if args.doc_types:
        doc_type_codes = [code.strip() for code in args.doc_types.split(",")]
        logger.info(f"Filtering for document types: {doc_type_codes}")

    try:
        # Call the new function
        structured_data = get_structured_data_for_company_date_range(
            edinet_code=args.edinet_code,
            start_date=args.start_date,
            end_date=args.end_date,
            doc_type_codes=doc_type_codes,
        )

        # Convert to JSON
        json_output = json.dumps(structured_data, indent=2, ensure_ascii=False)

        # Print to stdout
        print(json_output)

        # Also write to file if output path is provided
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            logger.info(f"JSON output also written to: {args.output}")

        logger.info(f"Successfully processed {len(structured_data)} documents")

    except Exception as e:
        logger.error(f"Error during company date range query: {e}")
        sys.exit(1)


def run_demo() -> None:
    """Runs the main demo workflow."""
    print_header()

    logger.info("Initializing...")

    # Define document types to look for
    # Only fetch document types for which we have specific processors to ensure
    # get_structured_data_from_zip_directory can create meaningful structured data.
    # If you want to fetch other types, ensure GenericReportProcessor is sufficient,
    # or add specific processors in document_processors.py
    doc_type_codes_to_fetch = [
        # "140",  # Quarterly Reports
        "160",  # Semi-Annual Reports
        "180",  # Extraordinary Reports
    ]

    days_back = DAYS_BACK

    # Fetch the most recent documents of the specified types
    docs_metadata, found_date = get_most_recent_documents(
        doc_type_codes_to_fetch,
        days_back=days_back,
    )

    if not docs_metadata:
        logger.error(
            f"No documents found meeting criteria in the last {days_back} days. Exiting demo."
        )
        return

    download_dir = DEFAULT_DOWNLOAD_DIR

    # download_documents function handles creating the directory
    download_documents(docs_metadata, download_dir)

    logger.info(f"\nProcessing downloaded documents from {found_date}...")

    # Process the downloaded zip files into structured data
    # We pass the keys of SUPPORTED_DOC_TYPES because get_structured_data_from_zip_directory
    # uses process_raw_csv_data which dispatches based on these codes.
    structured_document_data_list = get_structured_data_from_zip_directory(
        download_dir, doc_type_codes=list(SUPPORTED_DOC_TYPES.keys())
    )

    # Filter out metadata for documents that failed processing
    processed_doc_ids = {
        data.get("doc_id")
        for data in structured_document_data_list
        if data.get("doc_id")
    }
    docs_metadata_for_processed = [
        doc for doc in docs_metadata if doc.get("docID") in processed_doc_ids
    ]

    if not docs_metadata_for_processed:
        logger.error(
            "No documents were successfully processed into structured data. Exiting demo."
        )
        return

    # Create a map from doc_id to structured data for quick lookup
    structured_data_map = {
        data["doc_id"]: data
        for data in structured_document_data_list
        if "doc_id" in data
    }

    # LLM analysis section
    logger.info(f"\n{'*' * 80}")
    logger.info("Starting LLM Analysis...")
    logger.info(f"{'*' * 80}")

    # List to collect analysis results for later printing
    all_analysis_results = []

    # Analyze the first few *successfully processed* documents using LLM tools
    # Limit analysis to the configured number of processed documents
    num_to_analyze = min(ANALYSIS_LIMIT, len(docs_metadata_for_processed))
    docs_to_analyze_metadata = docs_metadata_for_processed[:num_to_analyze]

    logger.info(
        f"Analyzing the first {len(docs_to_analyze_metadata)} processed disclosures:"
    )

    # Define the order of analysis types for consistent output
    analysis_types_to_run = [
        "one_line_summary",
        "executive_summary",
    ]

    for i, doc_meta in enumerate(docs_to_analyze_metadata, 1):
        doc_id = doc_meta.get("docID")
        structured_data = structured_data_map.get(doc_id)
        doc_type_code = doc_meta.get("docTypeCode")
        company_name_en = (
            structured_data.get(
                "company_name_en", doc_meta.get("filerName", "Unknown Company")
            )
            if structured_data
            else doc_meta.get("filerName", "Unknown Company")
        )
        doc_type_name = SUPPORTED_DOC_TYPES.get(
            str(doc_type_code) if doc_type_code else "",
            str(doc_type_code) if doc_type_code else "Unknown",
        )
        submit_date_time_str = doc_meta.get("submitDateTime", "Date N/A")

        logger.info(
            f"\n[{i}/{num_to_analyze}] Analyzing {company_name_en} ({doc_type_name}, ID: {doc_id})..."
        )

        current_doc_analyses = {
            "doc_id": doc_id,
            "company_name_en": company_name_en,
            "doc_type": doc_type_name,
            "submit_date_time": submit_date_time_str,
            "analyses": {},  # Store results for this doc here
        }

        for analysis_type in analysis_types_to_run:
            if analysis_type not in TOOL_MAP:
                logger.warning(f"Skipping unknown analysis type: {analysis_type}")
                continue

            print_progress(f"  Generating '{analysis_type}' analysis...")
            try:
                # Call the analysis function and store the result
                if structured_data is None:
                    logger.warning(
                        f"No structured data available for doc_id {doc_id}, skipping analysis"
                    )
                    continue
                analysis_output = analyze_document_data(structured_data, analysis_type)
                current_doc_analyses["analyses"][analysis_type] = (
                    analysis_output  # Store output text or None
                )
            except Exception as e:
                logger.error(f"  Error during '{analysis_type}' analysis: {e}")
                # Store an error message if analysis fails
                current_doc_analyses["analyses"][analysis_type] = (
                    f"Error generating analysis: {e}"
                )

        all_analysis_results.append(
            current_doc_analyses
        )  # Add doc's results to the list
        logger.info(f"Finished analyses for document {i}/{num_to_analyze}.")

    print(f"\n\n{'=' * 80}")
    print("FINAL LLM ANALYSIS RESULTS")
    print(f"{'=' * 80}\n")

    if not all_analysis_results:
        print("No analysis results were collected.")
    else:
        for i, doc_results in enumerate(all_analysis_results, 1):
            print(f"{'-' * 80}")

            # per-document header lines - should all be strings
            doc_num_str = f"{i}/{len(all_analysis_results)}"
            company_name_str = doc_results.get("company_name_en", "Unknown Company")
            doc_type_str = doc_results.get("doc_type", "Unknown Type")
            doc_id_str = doc_results.get("doc_id", "N/A")
            date_str = doc_results.get("submit_date_time", "Date N/A")

            print(
                f"*** Document {doc_num_str} - {company_name_str} - {doc_type_str}: {doc_id_str} ***"
            )
            print(f"Submitted at: {date_str}")

            if not doc_results.get("analyses"):
                print("\n  No analyses were generated for this document.")
            else:
                for analysis_type in analysis_types_to_run:
                    output_text = doc_results["analyses"].get(analysis_type)

                    print(f"\n**{analysis_type.replace('_', ' ').title()}**")
                    if (
                        output_text is not None
                        and not isinstance(output_text, str)
                        or (
                            isinstance(output_text, str)
                            and not output_text.startswith("Error generating analysis:")
                        )
                    ):
                        # means valid output text
                        print(output_text)
                    elif output_text:  # means output_text is an error string
                        print(f"  {output_text}")
                    else:  # means output_text was None
                        print("  Analysis failed or returned empty.")

    print(f"\n{'=' * 80}")

    logger.info("\nDemo run complete. Analysis results printed above.")


if __name__ == "__main__":
    args = parse_args()

    # Check if any company date range query flags are provided
    company_query_flags = [args.edinet_code, args.start_date, args.end_date]
    if any(company_query_flags):
        # Validate that all required flags are provided
        if not all([args.edinet_code, args.start_date, args.end_date]):
            logger.error(
                "When using company date range query mode, --edinet-code, --start-date, and --end-date are all required"
            )
            sys.exit(1)

        logger.info("Running company date range query mode...")
        run_company_date_range_query(args)
    else:
        # No flags provided, run the existing demo
        logger.info("No CLI flags provided, running demo mode...")
        run_demo()
