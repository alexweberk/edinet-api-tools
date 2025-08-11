import datetime
import logging
import os
import tempfile
import zipfile
from typing import Any

from src.constants import (
    AUDITOR_REPORT_PREFIX,
    CSV_EXTENSION,
    MACOS_METADATA_DIR,
    SUPPORTED_DOC_TYPES,
    ZIP_EXTENSION,
)
from src.edinet.edinet_tools import download_documents, get_documents_for_date_range
from src.error_handlers import ErrorContext, log_exceptions
from src.llm_tools import TOOL_MAP
from src.logging_config import setup_logging
from src.processors.base_processor import StructuredDocumentData
from src.processors.extraordinary_processor import ExtraordinaryReportProcessor
from src.processors.generic_processor import GenericReportProcessor
from src.processors.semiannual_processor import SemiAnnualReportProcessor
from src.utils import read_csv_file

from .config import DAYS_BACK

setup_logging()
logger = logging.getLogger(__name__)


def get_most_recent_documents(
    doc_type_codes: list[str],
    days_back: int = DAYS_BACK,
    edinet_codes: list[str] | None = None,
    excluded_doc_type_codes: list[str] | None = None,
    require_sec_code: bool = True,
) -> tuple[list[dict[str, Any]], datetime.date | None]:
    """
    Fetch documents from the most recent day with filings within a date range.
    Searches back day by day up to `days_back`.

    Args:
        doc_type_codes: List of document type codes to filter by.
        days_back: Number of days to search back.
        edinet_codes: List of EDINET codes to filter by.
        excluded_doc_type_codes: List of document type codes to exclude.
        require_sec_code: Whether to require a security code.

    Returns:
        Tuple containing a list of documents and the date of the most recent documents found.
    """
    current_date = datetime.date.today()
    end_date = current_date  # Search up to today
    start_date = current_date - datetime.timedelta(
        days=days_back
    )  # Search back up to days_back

    logger.info(
        f"Searching for documents in the last {days_back} days ({start_date} to {end_date})..."
    )

    # Iterate backwards day by day from end_date to start_date
    date_to_check = end_date
    while date_to_check >= start_date:
        logger.info(f"Fetching documents for {date_to_check}...")
        try:
            # Get documents for a single date
            docs = get_documents_for_date_range(
                date_to_check,
                date_to_check,
                doc_type_codes=doc_type_codes,
                edinet_codes=edinet_codes,
                excluded_doc_type_codes=excluded_doc_type_codes,
                require_sec_code=require_sec_code,
            )

            if docs:
                logger.info(
                    f"Found {len(docs)} documents for {date_to_check}. Processing these."
                )

                return (
                    docs,
                    date_to_check,  # Return documents for the first day with results
                )

            logger.info(f"No documents found for {date_to_check}. Trying previous day.")
            date_to_check -= datetime.timedelta(days=1)

        except Exception as e:
            logger.error(f"Error fetching documents for {date_to_check}: {e}")
            # Continue to previous day even if one date fails

    logger.warning(
        f"No documents found in the last {days_back} days matching criteria."
    )
    return [], None


@log_exceptions(logger, reraise=False, return_value=None)
def get_structured_document_data_from_raw_csv(
    raw_csv_data: list[dict[str, Any]],
    doc_id: str,
    doc_type_code: str,
) -> StructuredDocumentData | None:
    """
    Dispatches raw CSV data to the appropriate document processor.

    Args:
        raw_csv_data: List of dictionaries from reading CSV files.
        doc_id: EDINET document ID.
        doc_type_code: EDINET document type code.

    Returns:
        Structured dictionary of the document's data, or None if processing failed.
    """
    processor_map = {
        "180": ExtraordinaryReportProcessor,
        "160": SemiAnnualReportProcessor,
        # Add other specific processors here
        # "140": QuarterlyReportProcessor,
    }
    default_processor = GenericReportProcessor

    processor_class = processor_map.get(doc_type_code, default_processor)
    logger.debug(
        f"Using processor {processor_class.__name__} for document type {doc_type_code} (doc_id: {doc_id})"
    )

    with ErrorContext(
        f"Processing document {doc_id} with {processor_class.__name__}",
        logger,
        reraise=False,
    ):
        processor = processor_class(raw_csv_data, doc_id, doc_type_code)
        return processor.process()


# ZIP file processing
def get_structured_data_from_zip_file(
    path_to_zip_file: str,
    doc_id: str,
    doc_type_code: str,
) -> dict[str, Any] | None:
    """
    Extract CSVs from a ZIP file, read them, and process into structured data
    using the appropriate document processor.

    :param path_to_zip_file: Path to the downloaded ZIP file.
    :param doc_id: EDINET document ID.
    :param doc_type_code: EDINET document type code.
    :return: Structured dictionary of the document's data, or None if processing failed.
    """
    raw_csv_data = []
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with zipfile.ZipFile(path_to_zip_file, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)
                logger.debug(
                    f"Extracted {os.path.basename(path_to_zip_file)} to {temp_dir}"
                )
            except zipfile.BadZipFile as e:
                logger.error(f"Bad ZIP file: {path_to_zip_file}. Error: {e}")
                return None
            except Exception as e:
                logger.error(
                    f"Error extracting {os.path.basename(path_to_zip_file)}: {e}"
                )
                return None

            # Find and read all CSV files within the extracted structure
            csv_file_paths = []
            for root, dirs, files in os.walk(temp_dir):
                # Exclude __MACOSX directory if present
                if MACOS_METADATA_DIR in dirs:
                    dirs.remove(MACOS_METADATA_DIR)
                for file in files:
                    if file.endswith(CSV_EXTENSION):
                        csv_file_paths.append(os.path.join(root, file))

            if not csv_file_paths:
                logger.warning(
                    f"No CSV files found in extracted zip: {os.path.basename(path_to_zip_file)}"
                )
                return None

            for file_path in csv_file_paths:
                # Skip auditor report files (start with 'jpaud')
                if os.path.basename(file_path).startswith(AUDITOR_REPORT_PREFIX):
                    logger.debug(
                        f"Skipping auditor report file: {os.path.basename(file_path)}"
                    )
                    continue

                csv_records = read_csv_file(file_path)
                if csv_records is not None:
                    raw_csv_data.append(
                        {"filename": os.path.basename(file_path), "data": csv_records}
                    )

            if not raw_csv_data:
                logger.warning(
                    f"No valid data extracted from CSVs in {os.path.basename(path_to_zip_file)}"
                )
                return None

            # Dispatch raw data to appropriate document processor
            structured_data = get_structured_document_data_from_raw_csv(
                raw_csv_data,
                doc_id,
                doc_type_code,
            )

            if structured_data:
                logger.info(
                    f"Successfully processed structured data for {os.path.basename(path_to_zip_file)}"
                )
                return structured_data
            else:
                logger.warning(
                    f"Document processor returned no data for {os.path.basename(path_to_zip_file)}"
                )
                return None

    except Exception as e:
        logger.error(f"Critical error processing zip file {path_to_zip_file}: {e}")
        # traceback.print_exc() # Uncomment for detailed traceback during debugging
        return None


def get_structured_data_from_zip_directory(
    directory_path: str,
    doc_type_codes: list[str] | None = None,
    doc_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Process all ZIP files in a directory containing EDINET documents.

    Args:
        directory_path: Path to the directory containing ZIP files.
        doc_type_codes: Optional list of doc type codes to process.
        doc_ids: Optional list of doc IDs to process.

    Returns:
        List of structured data dictionaries for each successfully processed document.
    """
    all_structured_data = []
    if not os.path.isdir(directory_path):
        logger.error(f"Directory not found: {directory_path}")
        return []

    zip_files = [
        f
        for f in os.listdir(directory_path)
        if f.endswith(ZIP_EXTENSION) and (doc_ids is None or f.split("-")[0] in doc_ids)
    ]
    total_files = len(zip_files)
    logger.info(f"Found {total_files} zip files in {directory_path} to process.")

    for i, filename in enumerate(zip_files, 1):
        file_path = os.path.join(directory_path, filename)
        try:
            # Filename format: docID-docTypeCode-filerName.zip
            parts = filename.split("-", 2)
            if len(parts) < 3:
                logger.warning(f"Skipping improperly named zip file: {filename}")
                continue
            doc_id = parts[0]
            doc_type_code = parts[1]
            # filer_name = parts[2].rsplit('.', 1)[0] # Not strictly needed here

            if doc_type_codes is not None and doc_type_code not in doc_type_codes:
                # logger.debug(f"Skipping {filename} (doc type {doc_type_code} not in target list)")
                continue

            logger.info(f"Processing {i}/{total_files}: `{filename}`")
            structured_data = get_structured_data_from_zip_file(
                file_path, doc_id, doc_type_code
            )

            if structured_data:
                all_structured_data.append(structured_data)

        except Exception as e:
            logger.error(f"Error processing zip file {filename}: {e}")
            # traceback.print_exc() # Uncomment for detailed traceback during debugging

    logger.info(
        f"Finished processing zip directory. Successfully extracted structured data for {len(all_structured_data)} documents."
    )
    return all_structured_data


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


def get_structured_data_for_company_date_range(
    edinet_code: str,
    start_date: datetime.date | str,
    end_date: datetime.date | str,
    doc_type_codes: list[str] | None = None,
    excluded_doc_type_codes: list[str] | None = None,
    require_sec_code: bool = True,
    download_dir: str | None = None,
) -> list[dict[str, Any]]:
    """Return structured data for filings by one company within a date range.

    Validates dates (YYYY-MM-DD if str), ensures start_date <= end_date,
    fetches documents via edinet_tools.get_documents_for_date_range filtered by
    the given edinet_code, downloads ZIPs to a target directory (create a subdir
    if download_dir is None), and converts ZIPs to structured dicts using
    get_structured_data_from_zip_directory.

    Args:
        edinet_code: EDINET code for the company to fetch documents for
        start_date: Start date for the date range (datetime.date or YYYY-MM-DD string)
        end_date: End date for the date range (datetime.date or YYYY-MM-DD string)
        doc_type_codes: Optional list of document type codes to include
        excluded_doc_type_codes: Optional list of document type codes to exclude
        require_sec_code: Whether to require a security code (default: True)
        download_dir: Directory to download files to (auto-generated if None)

    Returns:
        List of structured dictionaries (one per processed document).
    """
    # Parse and validate dates
    if isinstance(start_date, str):
        try:
            start_date_parsed = datetime.datetime.strptime(
                start_date, "%Y-%m-%d"
            ).date()
        except ValueError as e:
            raise ValueError(
                f"Invalid start_date format. Use 'YYYY-MM-DD'. Got: {start_date}"
            ) from e
    else:
        start_date_parsed = start_date

    if isinstance(end_date, str):
        try:
            end_date_parsed = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(
                f"Invalid end_date format. Use 'YYYY-MM-DD'. Got: {end_date}"
            ) from e
    else:
        end_date_parsed = end_date

    # Validate date range
    if start_date_parsed > end_date_parsed:
        raise ValueError(
            f"start_date ({start_date_parsed}) must be <= end_date ({end_date_parsed})"
        )

    logger.info(
        f"Fetching documents for EDINET code {edinet_code} from {start_date_parsed} to {end_date_parsed}"
    )

    # Create download directory if not provided
    if download_dir is None:
        download_dir = (
            f"downloads/company-{edinet_code}-{start_date_parsed}_{end_date_parsed}"
        )

    os.makedirs(download_dir, exist_ok=True)
    logger.info(f"Using download directory: {download_dir}")

    # Fetch documents for the company within the date range
    docs_metadata = get_documents_for_date_range(
        start_date=start_date_parsed,
        end_date=end_date_parsed,
        edinet_codes=[edinet_code],  # Filter by single EDINET code
        doc_type_codes=doc_type_codes,
        excluded_doc_type_codes=excluded_doc_type_codes,
        require_sec_code=require_sec_code,
    )

    if not docs_metadata:
        logger.info(
            f"No documents found for EDINET code {edinet_code} in the specified date range"
        )
        return []

    logger.info(f"Found {len(docs_metadata)} documents for {edinet_code}")

    # Download the documents
    download_documents(docs_metadata, download_dir)

    # Process the downloaded zip files into structured data
    # Use all supported document types for processing
    structured_document_data_list = get_structured_data_from_zip_directory(
        download_dir, doc_type_codes=list(SUPPORTED_DOC_TYPES.keys())
    )

    logger.info(
        f"Successfully processed {len(structured_document_data_list)} documents for {edinet_code}"
    )

    return structured_document_data_list
