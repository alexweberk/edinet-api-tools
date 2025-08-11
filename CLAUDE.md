# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This is a Python project using UV for package management with pyproject.toml configuration.

**Running main.py:**
```bash
uv run python main.py                    # Run demo mode
uv run python main.py --help            # Show available CLI options
```

**Company date range query mode:**
```bash
uv run python main.py --edinet-code E12345 --start-date 2024-01-01 --end-date 2024-01-31
uv run python main.py --edinet-code E12345 --start-date 2024-01-01 --end-date 2024-01-31 --doc-types "160,180" --output results.json
```

**Installing dependencies:**
```bash
uv sync
```

**Linting and code formatting:**
```bash
uv run ruff check .      # Check linting
uv run ruff format .     # Format code
uv run ruff check . --fix # Auto-fix issues
```

**Pre-commit hooks:**
```bash
uv run pre-commit install        # Install git hooks
uv run pre-commit run --all-files # Run on all files
```

**Installing LLM plugins for different models:**
```bash
llm install llm-anthropic  # For Claude models
llm install llm-gemini     # For Gemini models
llm install llm-gpt4all    # For local models
```

## Architecture Overview

This project provides tools for interacting with Japan's EDINET API v2 to download and analyze financial disclosure documents using Large Language Models via the `llm` library.

### Core Architecture Components

**Data Flow Pipeline:**
1. **EDINET API Interaction** (`src/edinet/edinet_tools.py`) → Fetch document lists and download ZIP files
2. **Data Processing** (`src/utils.py`) → Extract and clean CSV data from ZIP archives
3. **Document Processing** (`src/processors/`) → Transform raw CSV into structured data
4. **LLM Analysis** (`src/llm_tools/`) → Generate structured insights using Pydantic schemas
5. **Service Layer** (`src/services.py`) → Orchestrate the complete workflow

### Key Modules

- **`src/edinet/edinet_tools.py`**: EDINET API client with retry logic and error handling
- **`src/processors/`**: Document-type-specific processors that transform raw CSV data:
  - `base_processor.py`: Abstract base class defining the processor interface
  - `semiannual_processor.py`: Handles Semi-Annual Reports (160)
  - `extraordinary_processor.py`: Handles Extraordinary Reports (180)
  - `generic_processor.py`: Fallback processor for unsupported document types
- **`src/llm_tools/`**: LLM analysis framework using Pydantic schemas:
  - `base_tool.py`: Abstract base class for LLM analysis tools
  - `oneliner_tool.py`: Generates one-line summaries
  - `executive_summary_tool.py`: Generates executive summaries
  - `schemas.py`: Pydantic models for structured LLM output
- **`src/services.py`**: High-level service functions orchestrating the complete workflow
- **`src/utils.py`**: File processing utilities (encoding detection, CSV parsing, text cleaning)
- **`src/config.py`**: Environment configuration loading and validation
- **`src/config_validation.py`**: Pydantic-based configuration validation
- **`src/constants.py`**: Application constants including API URLs, element IDs, and document types
- **`src/exceptions.py`**: Custom exception classes for error handling
- **`src/error_handlers.py`**: Error handling decorators and context managers
- **`src/logging_config.py`**: Centralized logging configuration

### Document Processing System

The system uses a processor mapping pattern in `services.py:get_structured_document_data_from_raw_csv()`:
- Document type codes (160, 180, etc.) map to specific processor classes
- Each processor extracts relevant data using XBRL element IDs
- Falls back to `GenericReportProcessor` for unsupported document types
- All processors inherit from `BaseDocumentProcessor` and return `StructuredDocumentData`

### LLM Integration

Uses the `llm` library for model-agnostic LLM access:
- Supports multiple providers (OpenAI, Anthropic, Google, local models) via plugins
- Pydantic schemas ensure structured output (`OneLineSummary`, `ExecutiveSummary`)
- Fallback model configuration for reliability
- Tools are registered in `TOOL_MAP` for dynamic dispatch

## Configuration Requirements

The project uses Pydantic-based configuration validation with comprehensive error checking.

**Required Environment Variables:**
- `EDINET_API_KEY`: Japan EDINET API access key (required)

**LLM Configuration (at least one required):**
- `LLM_API_KEY` or `OPENAI_API_KEY`: LLM provider API key
- `LLM_MODEL`: Primary LLM model (default: gpt-4o)
- `LLM_FALLBACK_MODEL`: Backup model (default: gpt-4-turbo)

**Azure OpenAI Configuration (all required if using Azure):**
- `AZURE_OPENAI_API_KEY`: Azure API key
- `AZURE_OPENAI_ENDPOINT`: Azure endpoint URL
- `AZURE_OPENAI_API_VERSION`: API version (YYYY-MM-DD format)
- `AZURE_OPENAI_DEPLOYMENT`: Deployment name

**Optional Processing Configuration:**
- `MAX_RETRIES`: Maximum retry attempts (default: 3)
- `DELAY_SECONDS`: Delay between retries in seconds (default: 5)
- `ANALYSIS_LIMIT`: Maximum documents to analyze (default: 5)
- `DAYS_BACK`: Days to search back for recent documents (default: 7)

## Entry Points and CLI Usage

The application has two main modes:

**1. Demo Mode (default):**
- Fetches recent documents of specified types
- Downloads and processes them
- Runs LLM analysis on a limited number
- Usage: `uv run python main.py`

**2. Company Date Range Query Mode:**
- Fetches documents for a specific company within a date range
- Supports document type filtering
- Outputs structured JSON data
- Usage: `uv run python main.py --edinet-code <CODE> --start-date <DATE> --end-date <DATE>`

## Supported Document Types

Defined in `src/constants.py:SUPPORTED_DOC_TYPES`:
- 160: Semi-Annual Report
- 140: Quarterly Report
- 180: Extraordinary Report
- 350: Large Holding Report
- 030: Securities Registration Statement
- 120: Securities Report

## Adding New Analysis Tools

1. Define Pydantic schema in `src/llm_tools/schemas.py`
2. Create class inheriting from `BasePromptTool` in `src/llm_tools/`
3. Implement `create_prompt()` and `format_to_text()` methods
4. Set the `tool_name` class attribute
5. Add to `TOOL_MAP` in `src/llm_tools/__init__.py`

## Adding New Document Processors

1. Create class inheriting from `BaseDocumentProcessor` in `src/processors/`
2. Implement `process()` method with document-specific data extraction logic
3. Add to `processor_map` in `services.py:get_structured_document_data_from_raw_csv()`

## Project Structure

```
edinet-api-tools/
├── src/                           # Main source code
│   ├── config.py                  # Configuration loading and validation
│   ├── config_validation.py       # Pydantic configuration models
│   ├── constants.py               # Application constants and settings
│   ├── exceptions.py              # Custom exception classes
│   ├── error_handlers.py          # Error handling decorators
│   ├── logging_config.py          # Centralized logging setup
│   ├── services.py                # High-level service orchestration
│   ├── utils.py                   # File processing utilities
│   ├── edinet/                    # EDINET API integration
│   │   └── edinet_tools.py        # API client with retry logic
│   ├── processors/                # Document-specific processors
│   │   ├── base_processor.py      # Abstract base class
│   │   ├── generic_processor.py   # Fallback processor
│   │   ├── semiannual_processor.py # Semi-Annual Reports (160)
│   │   └── extraordinary_processor.py # Extraordinary Reports (180)
│   └── llm_tools/                 # LLM analysis framework
│       ├── base_tool.py           # Abstract base tool class
│       ├── schemas.py             # Pydantic output schemas
│       ├── oneliner_tool.py       # One-line summary tool
│       └── executive_summary_tool.py # Executive summary tool
├── main.py                        # CLI entry point
├── main.ipynb                     # Jupyter notebook for exploration
├── pyproject.toml                 # UV package configuration
├── downloads/                     # Downloaded ZIP files storage
└── docs/                          # Additional documentation
```

## Error Handling and Logging

The project implements comprehensive error handling:

- **Custom Exceptions**: Specific exception types in `src/exceptions.py` for different error categories
- **Error Decorators**: `@log_exceptions` decorator in `src/error_handlers.py` for consistent error logging
- **Context Managers**: `ErrorContext` for scoped error handling
- **Centralized Logging**: Consistent logging configuration across all modules
- **Graceful Degradation**: Failed document processing doesn't stop the entire pipeline

## Data Flow Details

**1. Document Discovery:**
- `edinet_tools.get_documents_for_date_range()` queries EDINET API for document metadata
- Returns list of document metadata dictionaries with docID, docTypeCode, filerName, etc.

**2. Document Download:**
- `edinet_tools.download_documents()` downloads ZIP files to specified directory
- Uses filename format: `{docID}-{docTypeCode}-{filerName}.zip`

**3. Document Processing:**
- `services.get_structured_data_from_zip_directory()` processes all ZIP files in directory
- Extracts CSV files, skips auditor reports (jpaud* files)
- Dispatches to appropriate processor based on document type code

**4. LLM Analysis:**
- `services.analyze_document_data()` applies LLM tools to structured data
- Tools generate formatted text output using Pydantic schemas
- Supports multiple analysis types (one-line summary, executive summary)

## Implementation Learnings: Company Date Range Query Feature

### Key Insights from Issue #2 Implementation

**Unexpected Challenge: Import Organization Complexity**
- *Expectation*: Simple import additions would suffice
- *Reality*: Ruff's strict import sorting required careful attention to import order and formatting
- *Learning*: The project uses aggressive linting that automatically reorganizes imports, requiring multiple formatting passes

**Surprise: Existing Architecture Was Perfectly Suited**
- *Expectation*: Would need to modify or extend existing functions significantly
- *Reality*: The existing `get_documents_for_date_range` function already supported filtering by `edinet_codes` as a list, making the implementation straightforward
- *Learning*: The modular architecture with clear separation between API calls, downloading, and processing made composition trivial

**Testing Reality vs Expectations**
- *Expectation*: Would need complex test setup or live API calls for validation
- *Reality*: Basic argument validation and empty result handling provided sufficient confidence in the implementation
- *Learning*: The existing error handling and logging infrastructure meant that runtime issues would be clearly visible to users

**Documentation Structure Insight**
- *Expectation*: Would need extensive documentation updates
- *Reality*: The existing CLAUDE.md structure already covered the architecture well enough that minimal updates were needed
- *Learning*: Well-structured initial documentation pays dividends during feature additions

**CLI Argument Design Challenge**
- *Expectation*: Complex validation logic would be needed for CLI arguments
- *Reality*: Python's argparse combined with the existing date validation in the core function provided clean separation of concerns
- *Learning*: Validation at the service layer rather than CLI layer keeps the CLI simple and reusable
