# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This is a Python project using standard package management with pip and requirements.txt. No build system like Poetry or specialized task runners are configured.

**Running the demo:**
```bash
python demo.py
```

**Installing dependencies:**
```bash
pip install -r requirements.txt
```

**Linting (flake8 is available):**
```bash
flake8 .
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
1. **EDINET API Interaction** (`edinet_tools.py`) → Fetch document lists and download ZIP files
2. **Data Processing** (`utils.py`) → Extract and clean CSV data from ZIP archives
3. **Document Processing** (`document_processors.py`) → Transform raw CSV into structured data
4. **LLM Analysis** (`llm_analysis_tools.py`) → Generate structured insights using Pydantic schemas

### Key Modules

- **`edinet_tools.py`**: EDINET API client with retry logic and error handling
- **`document_processors.py`**: Document-type-specific processors (`BaseDocumentProcessor`, `ExtraordinaryReportProcessor`, `SemiAnnualReportProcessor`) that transform raw CSV data into structured dictionaries
- **`llm_analysis_tools.py`**: LLM analysis framework using Pydantic schemas for structured output. Contains `BasePromptTool` class and specific tools like `OneLinerTool`, `ExecutiveSummaryTool`
- **`utils.py`**: File processing utilities (encoding detection, CSV parsing, text cleaning)
- **`config.py`**: Environment configuration, supported document types, LLM model settings

### Document Processing System

The system uses a processor mapping pattern in `document_processors.process_raw_csv_data()`:
- Document type codes (160, 180, etc.) map to specific processor classes
- Each processor extracts relevant data using XBRL element IDs
- Falls back to `GenericReportProcessor` for unsupported document types

### LLM Integration

Uses the `llm` library for model-agnostic LLM access:
- Supports multiple providers (OpenAI, Anthropic, Google, local models) via plugins
- Pydantic schemas ensure structured output (`OneLineSummary`, `ExecutiveSummary`)
- Fallback model configuration for reliability

## Configuration Requirements

**Required Environment Variables:**
- `EDINET_API_KEY`: Japan EDINET API access key
- `OPENAI_API_KEY` or `LLM_API_KEY`: LLM provider API key

**Optional Configuration:**
- `LLM_MODEL`: Primary LLM model (default: gpt-4o)
- `LLM_FALLBACK_MODEL`: Backup model (default: gpt-4-turbo)
- Azure OpenAI variables for Azure deployment

## Supported Document Types

Defined in `config.py`:
- 160: Semi-Annual Report
- 140: Quarterly Report  
- 180: Extraordinary Report
- 350: Large Holding Report
- 030: Securities Registration Statement
- 120: Securities Report

## Adding New Analysis Tools

1. Define Pydantic schema for desired output structure
2. Create class inheriting from `BasePromptTool`
3. Implement `create_prompt()` and `format_to_text()` methods
4. Add to `TOOL_MAP` in `llm_analysis_tools.py`

## Adding New Document Processors

1. Create class inheriting from `BaseDocumentProcessor`
2. Implement document-specific data extraction logic
3. Add to `processor_map` in `document_processors.process_raw_csv_data()`