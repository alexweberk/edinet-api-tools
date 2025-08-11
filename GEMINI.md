# Project Overview

This project, `edinet-api-tools`, is a Python-based command-line interface (CLI) for interacting with the Japanese EDINET API v2. Its primary purpose is to fetch, process, and analyze financial disclosure documents from EDINET. The key feature is its ability to use Large Language Models (LLMs) for structured analysis of the text data extracted from these documents.

The project is built using Python 3.12 and utilizes the `llm` library, which provides a flexible backend for using various LLMs like OpenAI, Claude, and Gemini. The application can be run in two modes: a demo mode that fetches recent documents and analyzes them, and a query mode that allows fetching documents for a specific company within a date range.

## Building and Running

### Setup

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: The `requirements.txt` file is not present in the provided file listing, but is mentioned in the `README.md`. I will assume it can be generated from `pyproject.toml` or is a missing file.)*

3.  **Set up environment variables:**
    Create a `.env` file by copying `.env.example` and add your EDINET and LLM API keys.

### Running the Application

The main entry point is `main.py`.

*   **Demo Mode:**
    To run the application in demo mode, which fetches and analyzes recent documents, execute:
    ```bash
    python main.py
    ```

*   **Company Date Range Query Mode:**
    To fetch documents for a specific company, use the following flags:
    ```bash
    python main.py --edinet-code <EDINET_CODE> --start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD>
    ```
    Optional flags for this mode include `--doc-types` and `--output`.

## Development Conventions

*   **Linting and Formatting:** The project uses `ruff` for linting and formatting, with configurations defined in `pyproject.toml`.
*   **Type Checking:** `mypy` is used for static type checking, with strict rules defined in `pyproject.toml`.
*   **Pre-commit Hooks:** The `.pre-commit-config.yaml` file suggests the use of pre-commit hooks to enforce code quality standards before committing.
*   **Modular Structure:** The codebase is organized into a `src` directory with modules for different functionalities like EDINET API interaction (`edinet/`), LLM tools (`llm_tools/`), document processing (`processors/`), and services (`services.py`).
*   **Configuration:** Application configuration is managed through environment variables loaded from a `.env` file, as defined in `src/config.py`.
*   **Logging:** The application uses the `logging` module for logging, with the configuration set up in `src/logging_config.py`.
