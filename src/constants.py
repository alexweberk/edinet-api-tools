# constants.py
"""
Application constants and configuration values.
"""

# API Configuration
EDINET_API_BASE_URL = "https://disclosure.edinet-fsa.go.jp/api/v2"
EDINET_DOCUMENT_API_BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"

# API Request Types
API_TYPE_METADATA_ONLY = "1"
API_TYPE_METADATA_AND_RESULTS = "2"
API_CSV_DOCUMENT_TYPE = "5"

# Retry Configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_DELAY_SECONDS = 5

# HTTP Status Codes
HTTP_SUCCESS = 200
HTTP_CLIENT_ERROR_START = 400
HTTP_SERVER_ERROR_END = 600

# File Processing
CSV_SEPARATOR = "\t"
ZIP_EXTENSION = ".zip"
CSV_EXTENSION = ".csv"
MACOS_METADATA_DIR = "__MACOSX"
AUDITOR_REPORT_PREFIX = "jpaud"

# Document Processing Limits
DEFAULT_ANALYSIS_LIMIT = 5
MAX_TEXT_BLOCKS_FOR_ONELINER = 3
MAX_PROMPT_CHAR_LIMIT = 8000
CSV_ENCODING_DETECTION_BYTES = 1024

# LLM Configuration
DEFAULT_LLM_MODEL = "gpt-4o"
DEFAULT_LLM_FALLBACK_MODEL = "gpt-4-turbo"

# Search Configuration
DEFAULT_DAYS_BACK = 7
DEFAULT_SEARCH_DAYS_BACK = 2

# Content Limits for LLM Analysis
MAX_CONTENT_PREVIEW_CHARS = 500
MAX_SUMMARY_WORDS = 30
MAX_COMPANY_DESCRIPTION_WORDS = 15
MAX_IMPACT_RATIONALE_WORDS = 25

# Common XBRL Element IDs
XBRL_ELEMENT_IDS = {
    "EDINET_CODE": "jpdei_cor:EDINETCodeDEI",
    "COMPANY_NAME_JA": "jpdei_cor:FilerNameInJapaneseDEI",
    "COMPANY_NAME_EN": "jpdei_cor:FilerNameInEnglishDEI",
    "DOCUMENT_TYPE": "jpdei_cor:DocumentTypeDEI",
    "DOCUMENT_TITLE_COVER": "jpcrp-esr_cor:DocumentTitleCoverPage",
    "DOCUMENT_TITLE": "jpcrp_cor:DocumentTitle",
}

# Extraordinary Report Specific Element IDs
EXTRAORDINARY_REPORT_ELEMENT_IDS = [
    "jpcrp-esr_cor:ResolutionOfBoardOfDirectorsDescription",
    "jpcrp-esr_cor:SummaryOfReasonForSubmissionDescription",
    "jpcrp-esr_cor:ContentOfDecisionsDescription",
    "jpcrp-esr_cor:DateOfResolutionOfBoardOfDirectors",
    "jpcrp-esr_cor:DateOfOccurrence",
    "jpcrp-esr_cor:SummaryOfAgreementDescription",
    "jpcrp-esr_cor:DetailsOfTransactionPartiesDescription",
    "jpcrp-esr_cor:RationaleForTransactionDescription",
    "jpcrp-esr_cor:ImpactOnBusinessResultsDescription",
]

# Text cleaning patterns
TEXT_REPLACEMENTS = {
    "FULL_WIDTH_SPACE": "\u3000",
    "REGULAR_SPACE": " ",
}

# Directory names
DEFAULT_DOWNLOAD_DIR = "./downloads"

# Logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
