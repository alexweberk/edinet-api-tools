# utils.py
import logging
import os

import chardet
import pandas as pd

from src.constants import CSV_ENCODING_DETECTION_BYTES, CSV_SEPARATOR

logger = logging.getLogger(__name__)


def print_header() -> None:
    """Prints a stylized header using logging."""
    logger.info("=" * 80)
    logger.info("EDINET API x Structured LLM Analysis Demo")
    logger.info("=" * 80)


def print_progress(message: str) -> None:
    """Logs a progress message."""
    logger.info(message)


# Encoding and file reading
def detect_encoding(file_path: str) -> str | None:
    """Detect encoding of a file."""
    try:
        with open(file_path, "rb") as file:
            raw_data = file.read(
                CSV_ENCODING_DETECTION_BYTES
            )  # Read only first bytes for speed
        result = chardet.detect(raw_data)
        logger.debug(
            f"Detected encoding {result['encoding']} with confidence {result['confidence']} for {os.path.basename(file_path)}"
        )
        return result["encoding"]
    except OSError as e:
        logger.error(f"Error detecting encoding for {file_path}: {e}")
        return None


def read_csv_file(file_path: str) -> list[dict[str, str | None]] | None:
    """Read a tab-separated CSV file trying multiple encodings."""
    detected_encoding = detect_encoding(file_path)

    # Prioritize detected encoding, then common ones for EDINET, then broad set
    encodings = [detected_encoding] if detected_encoding else []
    encodings.extend(
        [
            "utf-16",
            "utf-16le",
            "utf-16be",
            "utf-8",
            "shift-jis",
            "euc-jp",
            "iso-8859-1",
            "windows-1252",
        ]
    )

    # Remove duplicates while preserving order
    for encoding in list(dict.fromkeys(encodings)):
        if not encoding:
            continue
        try:
            # Use low_memory=False to avoid DtypeWarning on mixed types
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                sep=CSV_SEPARATOR,
                dtype=str,
                low_memory=False,
            )
            logger.debug(
                f"Successfully read {os.path.basename(file_path)} with encoding {encoding}"
            )
            # Replace NaN with None to handle missing values consistently
            df = df.replace({float("nan"): None, "": None})
            return df.to_dict(orient="records")  # type: ignore[return-value]
        except (
            UnicodeDecodeError,
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
        ) as e:
            logger.debug(
                f"Failed to read {os.path.basename(file_path)} with encoding {encoding}: {e}"
            )
            continue
        except Exception as e:
            logger.error(
                f"An unexpected error occurred reading {os.path.basename(file_path)} with encoding {encoding}: {e}"
            )
            continue

    logger.error(
        f"Failed to read {file_path}. Unable to determine correct encoding or format."
    )
    return None
