# Apify Hackathon Actor

Python-based Apify Actor using `uv` for package management.

## Project Structure

```
.
├── .actor/
│   ├── actor.json          # Actor configuration
│   └── input_schema.json   # Input schema definition
├── src/
│   └── main.py            # Main actor entry point
├── Dockerfile             # Docker container definition
├── pyproject.toml         # Python project configuration (uv)
├── uv.lock                # Locked dependencies
└── README.md              # This file
```

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- [Apify CLI](https://docs.apify.com/cli) (for deployment)

## Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python** (if needed):
   ```bash
   uv python install 3.12
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

## Development

### Run locally

```bash
# Run the actor locally
apify run

# Run with specific input file
apify run --input-file input.json

# Run with clean storage
apify run --purge
```

### Using uv directly

```bash
# Run the actor using uv
uv run python src/main.py

# Install development dependencies
uv sync --group dev
```

## Code Quality

### Ruff - Fast Python Linter

Ruff is configured to check code quality, import sorting, and common issues.

```bash
# Check code for issues
uv run ruff check src/

# Auto-fix issues (safe fixes)
uv run ruff check --fix src/

# Auto-fix issues (including unsafe fixes)
uv run ruff check --fix --unsafe-fixes src/

# Check specific file
uv run ruff check src/main.py

# Show all available rules
uv run ruff rule --all
```

### Other Tools

```bash
# Run tests (when configured)
uv run pytest

# Format code
uv run black src/

# Type check
uv run mypy src/
```

## Deployment

```bash
# Login to Apify
apify login

# Deploy to Apify platform
apify push
```

## Input Schema

The actor accepts the following input parameters (defined in `.actor/input_schema.json`):

- `startUrls`: Array of URLs to start processing from
- `maxRequestsPerCrawl`: Maximum number of requests to process (default: 100)
- `proxyConfiguration`: Proxy settings for the actor

## Storage

The actor uses Apify's storage systems:

- **Dataset**: For structured results (`Actor.pushData()`)
- **Key-Value Store**: For configuration and final outputs (`Actor.setValue()` / `Actor.getValue()`)
- **Request Queue**: For managing URLs to crawl (if using crawlers)

## Resources

- [Apify Python SDK Documentation](https://docs.apify.com/sdk/python/)
- [Apify Actors Documentation](https://docs.apify.com/actors)
- [uv Documentation](https://github.com/astral-sh/uv)
- [Agents.md](./Agents.md) - Development guidelines
