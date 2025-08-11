import datetime
import logging
import os
import time
from typing import Any

import httpx

from src.constants import (
    API_CSV_DOCUMENT_TYPE,
    API_TYPE_METADATA_AND_RESULTS,
    EDINET_API_BASE_URL,
    EDINET_DOCUMENT_API_BASE_URL,
    HTTP_CLIENT_ERROR_START,
    HTTP_SERVER_ERROR_END,
    HTTP_SUCCESS,
    SUPPORTED_DOC_TYPES,
)
from src.error_handlers import ErrorContext, handle_api_errors
from src.exceptions import (
    EdinetConnectionError,
    EdinetDocumentFetchError,
    EdinetRetryExceededError,
    ValidationError,
)

from ..config import DELAY_SECONDS, EDINET_API_KEY, MAX_RETRIES

# Use module-specific logger
logger = logging.getLogger(__name__)


# API interaction functions
def fetch_documents_list(
    date: str | datetime.date,
    api_type: int = int(API_TYPE_METADATA_AND_RESULTS),
    max_retries: int = MAX_RETRIES,
    delay_seconds: int = DELAY_SECONDS,
) -> dict[str, Any]:
    """
    Retrieve disclosure documents from EDINET API for a specified date with retries.
    """
    if isinstance(date, str):
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")  # Validate format
            date_str = date  # Use the original string if valid
        except ValueError as e:
            raise ValidationError(
                f"Invalid date string. Use format 'YYYY-MM-DD'. Got: {date}"
            ) from e
    elif isinstance(date, datetime.date):
        date_str = date.strftime("%Y-%m-%d")
    else:
        # This should never happen, but just in case
        raise ValidationError(
            f"Date must be 'YYYY-MM-DD' or datetime.date. Got: {date}"
        )

    url = f"{EDINET_API_BASE_URL}/documents.json"
    params = {
        "date": date_str,
        "type": str(api_type),  # '1' is metadata only; '2' is metadata and results
        "Subscription-Key": EDINET_API_KEY,
        # TODO: Add other parameters as needed
    }

    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1} to fetch documents for {date_str}...")
            with httpx.Client() as client:
                response = client.get(url, params=params)

                # Check for non-200 status codes
                if response.status_code != HTTP_SUCCESS:
                    logger.error(
                        f"API returned status code {response.status_code} for date {date_str}."
                    )
                    # Attempt to read error body if available
                    try:
                        error_body = response.text
                        logger.error(f"Error body: {error_body}")
                    except Exception:
                        pass
                    # If it's a client error (4xx) or server error (5xx), might be retryable
                    if (
                        HTTP_CLIENT_ERROR_START
                        <= response.status_code
                        < HTTP_SERVER_ERROR_END
                        and attempt < max_retries - 1
                    ):
                        logger.warning(f"Retrying in {delay_seconds}s...")
                        time.sleep(delay_seconds)
                        continue  # Retry
                    else:
                        # Non-retryable error or last attempt
                        response.raise_for_status()

                data = response.json()
                logger.info(f"Successfully fetched documents for {date_str}.")
                return data

        except httpx.HTTPError as e:
            logger.error(f"HTTP Error fetching documents for {date_str}: {e}")
            if attempt < max_retries - 1:
                logger.warning(f"Retrying in {delay_seconds}s...")
                time.sleep(delay_seconds)
            else:
                logger.error("Max retries reached for fetching documents.")
                raise EdinetConnectionError(
                    f"Failed to fetch documents for {date_str} after {max_retries} attempts"
                ) from e
        except Exception as e:
            logger.error(
                f"An unexpected error occurred fetching documents for {date_str}: {e}"
            )
            if attempt < max_retries - 1:
                logger.warning(f"Retrying in {delay_seconds}s...")
                time.sleep(delay_seconds)
            else:
                logger.error("Max retries reached for fetching documents.")
                raise EdinetConnectionError(
                    f"Failed to fetch documents for {date_str} after {max_retries} attempts"
                ) from e

    # This line should theoretically not be reached if max_retries > 0
    raise EdinetRetryExceededError("Failed to fetch documents after multiple retries.")


def fetch_document(
    doc_id: str,
    max_retries: int = MAX_RETRIES,
    delay_seconds: int = DELAY_SECONDS,
) -> bytes:
    """
    Retrieve a specific document from EDINET API with retries and return raw bytes.

    Args:
        doc_id: The ID of the document to fetch.
        max_retries: Maximum number of retries.
        delay_seconds: Delay between retries.

    Returns:
        The raw bytes of the document.
    """
    url = f"{EDINET_DOCUMENT_API_BASE_URL}/documents/{doc_id}"
    params = {
        "type": API_CSV_DOCUMENT_TYPE,  # CSV document format
        "Subscription-Key": EDINET_API_KEY,
    }

    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1} to fetch document {doc_id}...")
            with httpx.Client() as client:
                response = client.get(url, params=params)

                # Check for non-200 status codes
                if response.status_code != HTTP_SUCCESS:
                    logger.error(
                        f"API returned status code {response.status_code} for document {doc_id}."
                    )
                    try:
                        error_body = response.text
                        logger.error(f"Error body: {error_body}")
                    except Exception:
                        pass

                    if 400 <= response.status_code < 600 and attempt < max_retries - 1:
                        logger.warning(f"Retrying in {delay_seconds}s...")
                        time.sleep(delay_seconds)
                        continue  # Retry
                    else:
                        response.raise_for_status()

                content = response.content
                logger.info(f"Successfully fetched document {doc_id}.")
                return content

        except httpx.HTTPError as e:
            logger.error(f"HTTP Error fetching document {doc_id}: {e}")
            if attempt < max_retries - 1:
                logger.warning(f"Retrying in {delay_seconds}s...")
                time.sleep(delay_seconds)
            else:
                logger.error("Max retries reached for fetching document.")
                raise EdinetDocumentFetchError(
                    f"Failed to fetch document {doc_id} after {max_retries} attempts"
                ) from e
        except Exception as e:
            logger.error(
                f"An unexpected error occurred fetching document {doc_id}: {e}"
            )
            if attempt < max_retries - 1:
                logger.warning(f"Retrying in {delay_seconds}s...")
                time.sleep(delay_seconds)
            else:
                logger.error("Max retries reached for fetching document.")
                raise EdinetDocumentFetchError(
                    f"Failed to fetch document {doc_id} after {max_retries} attempts"
                ) from e

    raise EdinetRetryExceededError(
        f"Failed to fetch document {doc_id} after multiple retries."
    )


@handle_api_errors
def save_document_content(doc_content: bytes, output_path: str) -> None:
    """Save the document content (bytes) to file."""
    with ErrorContext(f"Saving document to {output_path}", logger):
        with open(output_path, "wb") as file_out:
            file_out.write(doc_content)
        logger.info(f"Saved document content to {output_path}")


def download_documents(
    docs: list[dict[str, Any]], download_dir: str = "./downloads"
) -> None:
    """
    Download all documents in the provided list.
    """
    os.makedirs(download_dir, exist_ok=True)
    logger.info(f"Ensured download directory exists: {download_dir}")

    total_docs = len(docs)
    logger.info(f"Starting download of {total_docs} documents.")

    for i, doc in enumerate(docs, 1):
        doc_id = doc.get("docID")
        doc_type_code = doc.get("docTypeCode")
        filer = doc.get("filerName")

        if not doc_id or not doc_type_code or not filer:
            logger.warning(
                f"Skipping document {i}/{total_docs} due to missing metadata: {doc}"
            )
            continue

        save_name = f"{doc_id}-{doc_type_code}-{filer}.zip"
        output_path = os.path.join(download_dir, save_name)

        logger.info(f"Downloading {i}/{total_docs}: `{save_name}`")

        if not os.path.exists(output_path):
            try:
                # make GET request to `documents/{docID}` endpoint
                doc_content = fetch_document(doc_id)
                save_document_content(doc_content, output_path)
            except Exception as e:
                logger.error(f"Error downloading and saving {save_name}: {e}")
        else:
            # logger.info(f"File already exists: {save_name}")
            pass  # Keep this silent unless debugging needed

    logger.info(f"Download process complete. Files saved to: `{download_dir}`")


# Document filtering and processing
def filter_documents(
    docs: list[dict[str, Any]],
    edinet_codes: list[str] | str | None = None,
    doc_type_codes: list[str] | str | None = None,
    excluded_doc_type_codes: list[str] | str | None = None,
    require_sec_code: bool = True,
) -> list[dict[str, Any]]:
    """Filter list of documents by EDINET codes and document type codes."""
    if edinet_codes is None:
        edinet_codes = []
    elif isinstance(edinet_codes, str):
        edinet_codes = [edinet_codes]
    if doc_type_codes is None:
        doc_type_codes = []
    elif isinstance(doc_type_codes, str):
        doc_type_codes = [doc_type_codes]
    if excluded_doc_type_codes is None:
        excluded_doc_type_codes = []
    elif isinstance(excluded_doc_type_codes, str):
        excluded_doc_type_codes = [excluded_doc_type_codes]

    filtered_list = []
    for doc in docs:
        # Basic checks
        if "docID" not in doc or "docTypeCode" not in doc or "filerName" not in doc:
            logger.warning(f"Skipping document with incomplete metadata: {doc}")
            continue

        # Check for supported document types (optional, but good practice)
        if doc["docTypeCode"] not in SUPPORTED_DOC_TYPES:
            # logger.debug(f"Skipping document type {doc['docTypeCode']} ({doc['filerName']}) - not supported.")
            continue  # Skip document types we don't explicitly support analysis for

        # Apply EDINET code filter
        if edinet_codes and doc.get("edinetCode") not in edinet_codes:
            continue

        # Apply document type code filter
        if doc_type_codes and doc["docTypeCode"] not in doc_type_codes:
            continue

        # Apply excluded document type code filter
        if doc["docTypeCode"] in excluded_doc_type_codes:
            continue

        # Apply require securities code filter
        if require_sec_code and doc.get("secCode") is None:
            continue

        filtered_list.append(doc)

    logger.info(
        f"Filtered down to {len(filtered_list)} documents from initial list of {len(docs)}."
    )
    return filtered_list


def get_documents_for_date_range(
    start_date: datetime.date,
    end_date: datetime.date,
    edinet_codes: list[str] | None = None,
    doc_type_codes: list[str] | None = None,
    excluded_doc_type_codes: list[str] | None = None,
    require_sec_code: bool = True,
) -> list[dict[str, Any]]:
    """
    Retrieve and filter documents for a date range.

    Args:
        start_date: Start date for the date range.
        end_date: End date for the date range.
        edinet_codes: List of EDINET codes to filter by.
        doc_type_codes: List of document type codes to filter by.
        excluded_doc_type_codes: List of document type codes to exclude.
        require_sec_code: Whether to require a security code.

    Returns:
        List of documents that match the criteria.
    """
    if edinet_codes is None:
        edinet_codes = []
    if doc_type_codes is None:
        doc_type_codes = []
    if excluded_doc_type_codes is None:
        excluded_doc_type_codes = []
    matching_docs = []
    current_date = start_date
    while current_date <= end_date:
        try:
            docs_res = fetch_documents_list(date=current_date)
            if docs_res and docs_res.get("results"):
                logger.info(
                    f"Found {len(docs_res['results'])} documents on EDINET for {current_date}."
                )
                filtered_docs = filter_documents(
                    docs_res["results"],
                    edinet_codes,
                    doc_type_codes,
                    excluded_doc_type_codes,
                    require_sec_code,
                )
                matching_docs.extend(filtered_docs)
                logger.info(
                    f"Added {len(filtered_docs)} matching documents for {current_date}."
                )
            elif docs_res and docs_res.get("results") is None:
                logger.info(f"No documents listed for {current_date}.")
            elif not docs_res:
                logger.warning(f"Empty response received for {current_date}.")

        except Exception as e:
            logger.error(f"Error processing documents for date {current_date}: {e}")
            # Continue to next date even if one date fails
        finally:
            current_date += datetime.timedelta(days=1)

    logger.info(
        f"Finished retrieving documents for date range. Total matching documents: {len(matching_docs)}"
    )
    return matching_docs
