[![ci-tests](https://github.com/AlessioMartello/umbra-sync/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/AlessioMartello/umbra-sync/actions/workflows/tests.yaml)

[![codecov](https://codecov.io/github/alessiomartello/umbra-sync/graph/badge.svg?token=3OXO8DRNXY)](https://codecov.io/github/alessiomartello/umbra-sync)

# Umbra Sync

Umbra Sync is an automated contact synchronization tool that bridges Microsoft Outlook and Monday.com. It intelligently extracts contact information from your Outlook inbox and sent items, then synchronizes it with a Monday.com board—creating new contacts and updating existing ones with missing information.

## Overview

Umbra Sync solves the problem of maintaining accurate contact databases across multiple platforms. Instead of manually copying contact information between Outlook and Monday.com, this tool:

- Fetches new and recent emails from your Outlook inbox (since last sync)
- Extracts contact details (email, name, phone, LinkedIn profile)
- Identifies trusted senders from your sent items
- Compares against existing Monday.com contacts
- Creates new contacts for unknown senders
- Updates existing contacts with missing fields from new emails
- Maintains a watermark to avoid reprocessing

## Key Features

- **Bidirectional Awareness**: Builds trust from your own sent emails to filter inbox messages
- **Incremental Sync**: Uses watermarking to process only new emails since last run
- **Smart Matching**: Matches contacts by email address to identify duplicates
- **Selective Updates**: Only updates fields that are missing in Monday.com (preserves existing data)
- **Robust Error Handling**: Continues processing even if individual emails fail
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Async Support**: Uses async/await for efficient API calls
- **Retry Strategy**: Automatic retry logic for transient API failures

## Project Tooling

This project uses modern Python development tools for dependency management, testing, and code quality:

### Core Tools

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.12+ | Runtime environment |
| **[mise](https://mise.jdx.dev/)** | Latest | Tool version manager - manages Python and uv versions |
| **[uv](https://docs.astral.sh/uv/)** | Latest | Fast Python package installer/resolver (replaces pip/venv) |
| **[pytest](https://pytest.org/)** | 9.0.3+ | Testing framework for unit and integration tests |
| **[ruff](https://docs.astral.sh/ruff/)** | 0.15.9+ | Fast Python linter and formatter (replaces black, isort, flake8) |

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **httpx** | 0.28.1+ | Async HTTP client for API calls |
| **msal** | 1.35.1+ | Microsoft Authentication Library for Azure/Outlook auth |
| **pydantic** | 2.12.5+ | Data validation and type hints |
| **tenacity** | 9.1.4+ | Retry library with exponential backoff |
| **beautifulsoup4** | 4.14.3+ | HTML/XML parsing for email content |
| **python-dotenv** | 1.2.2+ | Environment variable loading from `.env` files |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **ipykernel** | 7.2.0+ | Jupyter kernel for interactive notebooks |
| **ruff** | 0.15.9+ | Linting and code formatting |

### Configuration Files

- **`pyproject.toml`**: Project metadata, dependencies, and tool configurations
- **`mise.toml`**: Tool versions (Python 3.12) and environment setup
- **`pytest.ini`** (in `pyproject.toml`): Test discovery configuration

### Workflow

```
Development Workflow:
┌─────────────────┐
│  mise install   │  ← Install Python 3.12 & uv
└────────┬────────┘
         ↓
┌─────────────────┐
│   uv sync       │  ← Install all dependencies
└────────┬────────┘
         ↓
┌─────────────────┐
│  ruff format    │  ← Format code
└────────┬────────┘
         ↓
┌─────────────────┐
│  ruff check     │  ← Lint code
└────────┬────────┘
         ↓
┌─────────────────┐
│    pytest       │  ← Run tests
└────────┬────────┘
         ↓
┌─────────────────┐
│ python src/main │  ← Run application
└─────────────────┘
```

## Architecture

### Components

```
umbra-sync/
├── src/
│   ├── main.py                 # Main orchestration logic
│   ├── clients/
│   │   ├── outlk.py           # Outlook API client
│   │   └── mday.py            # Monday.com API client
│   └── utils/
│       ├── data_models.py     # Pydantic models (Contact)
│       ├── logger.py          # Logging configuration
│       ├── retry_strategy.py  # Retry decorator
│       ├── transforms.py      # Email/contact transformations
│       ├── watermark.py       # Sync state management
│       └── monitoring.py      # Job summary tracking
├── tests/
│   └── test_transforms.py     # Unit tests
├── pyproject.toml             # Project metadata & dependencies
├── mise.toml                  # Tool version management
└── README.md                  # This file
```

### Data Flow

```
1. Load last sync timestamp (watermark)
   ↓
2. Fetch Outlook Inbox (since watermark)
   ↓
3. Fetch Outlook Sent Items
   ↓
4. Extract trusted recipient emails from Sent Items
   ↓
5. Filter Inbox by trusted contacts
   ↓
6. Deduplicate Inbox
   ↓
7. Fetch existing Monday.com contacts
   ↓
8. For each inbox email:
   - Parse contact details
   - Match against Monday.com (by email)
   - If new: add to create list
   - If existing but missing fields: add to update list
   - Otherwise: skip
   ↓
9. Create new contacts in Monday.com
   ↓
10. Update existing Monday.com contacts
    ↓
11. Save new watermark
    ↓
12. Write job summary
```

## Prerequisites

- **Python 3.12+**
- **Microsoft Outlook Account** with API access (Entra ID / Azure AD)
- **Monday.com Account** with a board for contacts
- **API Credentials**:
  - Azure Client ID (for Outlook)
  - Outlook Refresh Token
  - Monday.com API Key
  - Monday.com Board ID

### Getting API Credentials

#### Azure / Outlook Setup

1. Go to [Azure Portal](https://portal.azure.com)
2. Register a new application (or use existing)
3. Note the Client ID
4. Set Redirect URI: `http://localhost`
5. Create an auth flow to get Refresh Token (or use existing MSAL token)

#### Monday.com Setup

1. Go to your Monday.com workspace
2. Settings → API & Integrations → API Tokens
3. Create a new personal API token
4. Create a dedicated contact board (or use existing)
5. Note the board ID (visible in URL: `board/12345`)
6. Go to the board and note the column IDs for email, phone, and LinkedIn

## Installation

### Using `mise` and `uv`

```bash
# Clone the repository
git clone <repository-url>
cd umbra-sync

# mise will automatically set up Python 3.12
mise install

# Create virtual environment (automatically done by mise)
uv sync
```

## Configuration

Create a `.env` file in the project root with the following environment variables:

```env
# Outlook / Azure Configuration
AZURE_CLIENT_ID=your_azure_client_id
REFRESH_TOKEN=your_outlook_refresh_token

# Monday.com Configuration
MONDAY_API_KEY=your_monday_api_key
MONDAY_BOARD_ID=your_board_id_number

# Optional
DEBUG=false
```

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `AZURE_CLIENT_ID` | Azure AD application client ID | Yes | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `REFRESH_TOKEN` | Outlook refresh token | Yes | `MCwCA...` |
| `MONDAY_API_KEY` | Monday.com personal API token | Yes | `eyJhbGc...` |
| `MONDAY_BOARD_ID` | Monday.com board ID | Yes | `1234567890` |
| `DEBUG` | Enable debug logging | No | `false` |

## Usage

### Run Sync

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the sync
python src/main.py
```

### Run with Debug Logging

```bash
DEBUG=true python src/main.py
```

### Run Tests

```bash
# Run all tests
pytest

```

## Configuration Details

### Monday.com Schema

The default column IDs used in `src/clients/mday.py`:

```python
COL_EMAIL = "email"           # Standard Monday column
COL_PHONE = "phone"           # Standard Monday column
COL_LINKEDIN = "text_mm274aw7"  # Custom LinkedIn field
```

**To customize**: Edit `COLUMN_IDS` in the `MondayClient` class to match your board's column configuration.

### Watermark / State

The watermark (last sync timestamp) is stored as:

```
.watermark         # Production watermark
```

This prevents reprocessing of old emails. Delete these files to force a full resync.

## Data Models

### Contact

```python
class Contact(BaseModel):
    email_address: EmailStr          # Required, validated email
    name: str                        # Required, min 1 character
    phone: Optional[str] = None      # Optional
    linkedin: Optional[str] = None   # Optional
    monday_id: Optional[str] = None  # Optional Monday.com item ID
```

## Logging

Logs are structured using a custom logger in `src/utils/logger.py`:

```python
from utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Message")
logger.warning("Warning")
logger.error("Error")
```

Log output includes:
- Timestamp
- Log level
- Module name
- Message


## Error Handling & Retry Strategy

The `@api_retry_strategy` decorator provides exponential backoff retry logic for transient failures:

```python
@api_retry_strategy
async def _post(self, query: str, mday_vars: dict = None) -> dict:
    # API call with automatic retries
    pass
```

**Individual email failures do not crash the sync**:

```python
try:
    outlook_contact = transforms.parse_email_to_contact(email)
    # Process contact...
except Exception as e:
    logger.warning(f"Skipping email due to processing error: {e}")
    continue  # Continue processing next email
```

## Development

### Project Structure

- **`src/main.py`**: Entry point and main orchestration logic
- **`src/clients/`**: API client implementations
  - `outlk.py`: Microsoft Outlook/Graph API client
  - `mday.py`: Monday.com GraphQL API client
- **`src/utils/`**: Utility modules
  - `data_models.py`: Pydantic models
  - `logger.py`: Logging configuration
  - `retry_strategy.py`: Retry decorator
  - `transforms.py`: Email/contact transformation logic
  - `watermark.py`: Sync state management
  - `monitoring.py`: Job summary tracking
- **`tests/`**: Unit tests
  - `test_transforms.py`: Tests for transform functions

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_transforms.py::test_filter_inbox -v

```

### Code Quality

This project uses **Ruff** for linting and formatting. Use before committing:

```bash
# Format code
ruff format src/ tests/

# Check for linting issues
ruff check src/ tests/

# Fix issues automatically
ruff check --fix src/ tests/
```

## Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| No contacts created | Sync completes but Monday board unchanged | Check watermark; ensure inbox has emails; verify Monday board ID |
| Duplicate contacts | Same contact appears multiple times | Contacts are matched by email; check for email variations |
| Phone/LinkedIn not updating | Fields remain empty in Monday | Ensure regex patterns in `transforms.py` match your data format |
| Script crashes | Unexpected error in logs | Check `.env` configuration; verify API credentials |
| Memory usage grows | Script hangs during pagination | Check for API response issues; verify network connectivity |

## Performance

- **Typical sync time**: 30-120 seconds (depends on inbox size)
- **Email processing**: ~100-200 emails per minute
- **API calls**: Batched where possible (async)

### Optimization Tips

1. **Filter before processing**: Use `DEBUG=true` and reasonable watermark
2. **Reduce scope**: Adjust `MONDAY_FIELDS_TO_CHECK` if not needed
3. **Parallel requests**: Already uses `asyncio` for concurrent API calls

## Contributing

To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run tests: `pytest`
5. Format code: `ruff format src/ tests/`
6. Commit and push
7. Open a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
