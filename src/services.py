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
    ZIP_EXTENSION,
)
from src.edinet.edinet_tools import get_documents_for_date_range
from src.error_handlers import ErrorContext, log_exceptions
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
    directory_path: str, doc_type_codes: list[str] | None = None
) -> list[dict[str, Any]]:
    """
    Process all ZIP files in a directory containing EDINET documents.

    :param directory_path: Path to the directory containing ZIP files.
    :param doc_type_codes: Optional list of doc type codes to process.
    :return: List of structured data dictionaries for each successfully processed document.
    """
    all_structured_data = []
    if not os.path.isdir(directory_path):
        logger.error(f"Directory not found: {directory_path}")
        return []

    zip_files = [f for f in os.listdir(directory_path) if f.endswith(ZIP_EXTENSION)]
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
