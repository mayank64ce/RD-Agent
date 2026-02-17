# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RD-Agent is an LLM-Agent framework for autonomous data science R&D. It automates hypothesis generation, experiment implementation, and iterative improvement across quantitative finance, Kaggle competitions, medical prediction, and paper-to-code extraction.

**Requirements**: Linux, Docker, Python 3.10 or 3.11, LLM API access.

## Common Commands

### Development Setup
```bash
make dev                   # Install package in editable mode with all dev dependencies
cp .env.example .env       # Configure LLM API keys and settings
```

### Linting
```bash
make lint                  # Run all linters (mypy → ruff → isort → black → toml-sort)
make auto-lint             # Auto-fix: isort, black, toml-sort
make mypy                  # Type check rdagent/core only
make ruff                  # Lint rdagent/core only
```

### Testing
```bash
make test                  # Full test suite with coverage (requires API keys)
make test-offline          # Offline tests only (no API calls, used in CI)
pytest test/path/test_file.py              # Run a single test file
pytest test/path/test_file.py::test_func   # Run a single test
```

### Running the Application
```bash
rdagent fin_factor         # Quantitative factor evolution
rdagent fin_model          # Model evolution
rdagent fin_quant          # Joint factor-model evolution
rdagent data_science       # Data science competitions
rdagent general_model <paper_url>  # Extract models from papers
rdagent ui                 # Streamlit web UI for execution traces
rdagent health_check       # Validate Docker and port configuration
```

## Code Style

- Line length: 120 characters
- Formatting: black with isort (profile: black)
- Type checking: mypy strict on `rdagent/core/`, gradually expanding
- Ruff linting applies to `rdagent/core/` only currently
- Commit messages: conventional commits format, max 100 char header
  - Types: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`
- pytest config: `addopts = "-l -s --durations=0"`, log_cli enabled

## Architecture

### Core Framework (`rdagent/core/`)

The evolving loop pattern drives all scenarios:

```
Scenario → Hypothesis → Experiment → Developer → Runner → Evaluator → Feedback → (repeat)
```

Key abstractions:
- **Scenario** (`scenario.py`): Problem definition (dataset, metrics, background)
- **Hypothesis** (`proposal.py`): Proposed improvement based on prior feedback
- **Experiment/Task** (`experiment.py`): Executable work units with code implementations
- **Developer** (`developer.py`): Converts experiments into runnable code (LLM-powered)
- **Evaluator** (`evaluation.py`): Provides feedback on execution results
- **EvolvingStrategy**: Strategy pattern for iterative improvement
- **KnowledgeBase** (`knowledge_base.py`): RAG-based knowledge storage

### Scenarios (`rdagent/scenarios/`)

Each scenario specializes the core abstractions:
- **`qlib/`**: Quantitative finance (factor mining, model development) using Qlib framework
- **`data_science/`**: Kaggle/medical competitions with automated feature engineering
- **`kaggle/`**: Kaggle-specific crawling and competition handling
- **`general_model/`**: Paper reading → model extraction → implementation

### Application Layer (`rdagent/app/`)

- **CLI** (`cli.py`): Typer-based entry point, registered as `rdagent` console script
- **Loop classes** (e.g., `FactorRDLoop`): Orchestrate the evolving loop with checkpointing and session continuation
- Each app command maps to a scenario-specific main function

### LLM Integration (`rdagent/oai/`)

- Default backend: LiteLLM (multi-provider support: OpenAI, Azure, DeepSeek, etc.)
- Separate configuration for chat and embedding models
- Caching support via `USE_CHAT_CACHE` / `USE_EMBEDDING_CACHE`

### Configuration System

- `pydantic-settings` based (`ExtendedBaseSettings` in `rdagent/core/conf.py`)
- Priority: init params → env vars → parent env vars → `.env` file → file secrets
- All settings configurable via environment variables
- `.env` file auto-loaded at CLI startup in `cli.py`

### Key Directories

- **`rdagent/components/`**: Reusable implementations (coder, proposal, runner, workflow, knowledge_management, document_reader)
- **`rdagent/log/`**: Logging infrastructure + Streamlit UI (`log/ui/`)
- **`rdagent/utils/`**: Helpers including `workflow/loop.py` (base loop), `env.py` (Docker environments)
- **`git_ignore_folder/`**: Default workspace directory for runtime artifacts (gitignored)
