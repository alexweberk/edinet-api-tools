# exceptions.py
"""
Custom exception classes for the EDINET API tools.
"""


class EdinetAPIError(Exception):
    """Base exception for EDINET API related errors."""

    pass


class EdinetConnectionError(EdinetAPIError):
    """Raised when connection to EDINET API fails."""

    pass


class EdinetDocumentFetchError(EdinetAPIError):
    """Raised when document fetching from EDINET API fails."""

    pass


class EdinetRetryExceededError(EdinetAPIError):
    """Raised when maximum retry attempts are exceeded."""

    pass


class DocumentProcessingError(Exception):
    """Base exception for document processing errors."""

    pass


class DocumentExtractionError(DocumentProcessingError):
    """Raised when document extraction from ZIP files fails."""

    pass


class DocumentParsingError(DocumentProcessingError):
    """Raised when parsing document content fails."""

    pass


class CSVReadError(DocumentProcessingError):
    """Raised when reading CSV files fails."""

    pass


class LLMAnalysisError(Exception):
    """Base exception for LLM analysis errors."""

    pass


class LLMModelUnavailableError(LLMAnalysisError):
    """Raised when LLM model is not available or configured."""

    pass


class LLMResponseParsingError(LLMAnalysisError):
    """Raised when parsing LLM response fails."""

    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


class ValidationError(Exception):
    """Raised when data validation fails."""

    pass
