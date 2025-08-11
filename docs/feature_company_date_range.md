# Feature: Fetch structured EDINET data for a company within a date range

### User story
As a user, I want to specify an edinet_code, start_date, and end_date, and get a list of structured data for that specific company only.

### Background
The project already supports:
- Fetching EDINET documents by date via `src/edinet/edinet_tools.py` (e.g., `fetch_documents_list`, `get_documents_for_date_range`, and `filter_documents`).
- Downloading ZIPs via `download_documents`.
- Transforming ZIP contents into structured data via `src/services.py` (e.g., `get_structured_data_from_zip_directory`) which dispatches to processors in `src/processors/*`.

This feature should compose existing building blocks to minimize new code.

### Scope (minimal)
- Add a new service function to fetch and return structured data for a single `edinet_code` within a date range.
- Optional, minimal CLI entry: allow running the feature from `main.py` when flags are provided, printing JSON to stdout. Default to current demo when flags are absent.
- Reuse existing filtering, downloading, and processing logic.

### API design
Add to `src/services.py`:

```python
from typing import Any, Optional
import datetime


def get_structured_data_for_company_date_range(
    edinet_code: str,
    start_date: datetime.date | str,
    end_date: datetime.date | str,
    doc_type_codes: Optional[list[str]] = None,
    excluded_doc_type_codes: Optional[list[str]] = None,
    require_sec_code: bool = True,
    download_dir: str | None = None,
) -> list[dict[str, Any]]:
    """Return structured data for filings by one company within a date range.
    Validates dates (YYYY-MM-DD if str), ensures start_date <= end_date,
    fetches documents via edinet_tools.get_documents_for_date_range filtered by
    the given edinet_code, downloads ZIPs to a target directory (create a subdir
    if download_dir is None), and converts ZIPs to structured dicts using
    get_structured_data_from_zip_directory.
    Returns a list of structured dictionaries (one per processed document).
    """
```

Notes:
- Accept both `datetime.date` and `YYYY-MM-DD` strings for dates.
- Use `edinet_tools.get_documents_for_date_range` with `[edinet_code]`.
- Use `SUPPORTED_DOC_TYPES.keys()` when dispatching to processors.
- Prefer a dedicated subdirectory like `downloads/company-{edinet_code}-{start_date}_{end_date}` if `download_dir` is not provided.

### CLI behavior (minimal)
Update `main.py` to support flags; when any of `--edinet-code/--start-date/--end-date` is present, run the new function and output JSON list to stdout. Otherwise run the existing demo.

Flags:
- `--edinet-code <str>` (required in this mode)
- `--start-date <YYYY-MM-DD>` (required)
- `--end-date <YYYY-MM-DD>` (required)
- `--doc-types <comma-separated>` (optional)
- `--output <path>` (optional; if provided, also write JSON there)

Example:
- `uv run python main.py --edinet-code E12345 --start-date 2024-01-01 --end-date 2024-03-31 --doc-types 160,180`

### Validation and errors
- Validate date format; return a clear error if invalid.
- Ensure `start_date <= end_date`; otherwise error.
- If no matching documents found, return an empty list and exit 0 for CLI.
- Propagate existing network/download errors through existing error handlers (`ErrorContext`, retries).

### Acceptance criteria
- Given valid inputs, function returns a list where each item is a structured dict built by the existing processors, filtered to the specified `edinet_code`.
- CLI prints valid JSON array to stdout when flags are used.
- Works for multiple `doc_type_codes` or defaults to all supported when not provided.
- No changes to existing behavior when flags are not passed.

### Out of scope
- LLM analysis of results.
- Multi-company query.
- New processors or schema changes.

### Implementation notes
- Reuse `src/edinet/edinet_tools.get_documents_for_date_range` and `filter_documents`.
- Reuse `src/edinet/edinet_tools.download_documents`.
- Reuse `src/services.get_structured_data_from_zip_directory`.
- Choose or create a dedicated `download_dir` to avoid mixing with demo downloads.
- Keep logging consistent with `logging_config.setup_logging()`.

### Test plan
- Unit: validate date parsing and error conditions.
- Smoke: run against a short date range for a known test `edinet_code` and verify non-empty/empty behavior.
- CLI: verify JSON output format and that default demo still runs when flags are absent.

### Tasks
1. Add `get_structured_data_for_company_date_range` to `src/services.py`.
2. Wire it to `edinet_tools.get_documents_for_date_range` and `download_documents`.
3. Call `get_structured_data_from_zip_directory` with `SUPPORTED_DOC_TYPES.keys()`.
4. Add argparse handling in `main.py` for the minimal flags and JSON output.
5. Update `README.md` with new usage example.
6. Add small unit tests for validation (if test infra exists); otherwise, add a simple smoke script under `examples/` (optional).
