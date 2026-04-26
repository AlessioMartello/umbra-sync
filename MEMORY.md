# Memory

This file captures project context, coding preferences, and working patterns
derived from conversations. Update as things change.

---

## Project: umbra-sync

### What It Does
Syncs contact information from Outlook emails into Monday.com. Extracts contact
details (name, email, phone, LinkedIn, job title, website, address) from email
signatures — both text and image-based — and creates or updates contacts on a
Monday.com board.

### Stack
- **Language:** Python 3.12+
- **Package manager:** uv (not pip) — always `uv sync`, `uv run`, `uv add`
- **Async:** `asyncio` + `aiohttp` throughout
- **Email source:** Microsoft Graph API (Outlook 365)
- **AI extraction:** Groq API — `llama-3.3-70b-versatile` for text, vision model for images
- **OCR:** Tesseract (free, local, GHA-compatible via `apt-get install tesseract-ocr`)
- **CRM target:** Monday.com GraphQL API
- **CI/CD:** GitHub Actions — scheduled hourly cron + `workflow_dispatch`
- **Environment:** WSL Ubuntu (development), GHA ubuntu-latest (CI)

### Architecture
```
Outlook (Graph API)
      ↓
Filter to trusted senders (appeared in sent items)
      ↓
Deduplicate by email address
      ↓
Extract contact: regex + phonenumbers + Groq NLP + Tesseract OCR (images)
      ↓
Match against existing Monday contacts (keyed by email)
      ↓
Create new / update missing or changed fields
      ↓
Update watermark
```

### Key Design Decisions
- **Trusted sender filter:** Only process emails from addresses we have sent to — avoids spam/newsletters polluting the CRM
- **Watermark pattern:** JSON file committed back to repo after each run — tracks last processed timestamp for incremental processing
- **Deduplication:** One contact per email address — most recent email wins
- **Groq free tier:** Used for NLP extraction — mindful of 100K TPD / 1K RPD limits on `llama-3.3-70b-versatile`
- **Tesseract before Groq vision:** OCR is free and local — only fall back to vision API if OCR yields nothing useful
- **`uniqueBody` not `body`:** Microsoft Graph — uniqueBody strips reply chains, essential for clean signature extraction
- **Signature tail:** Pass only last portion of email body to Groq, not full email — saves tokens
- **Monday returns 200 for errors:** Always check `data["errors"]` before using response
- **Source of truth:** Outlook is the source of truth — latest data overwrites Monday, except fields flagged as manually verified
- **Pipeline resilience:** One bad email must never crash the whole run — wrap per-item processing in try/except, log and skip

### Repo Structure
```
umbra-sync/
├── .agents/                          # owned by VS Code Claude extension
│   └── data-engineering.agent.md
├── .github/
│   └── workflows/
│       └── sync_contacts.yml
├── skills/                           # reference docs for Claude
│   ├── python/SKILL.md
│   ├── microsoft-graph/SKILL.md
│   ├── monday-com/SKILL.md
│   └── groq/SKILL.md
├── src/
│   ├── clients/
│   │   ├── outlk.py                  # Microsoft Graph / Outlook
│   │   └── mday.py                   # Monday.com GraphQL
│   ├── utils/
│   │   ├── logger.py
│   │   ├── retry_strategy.py         # tenacity decorators
│   │   ├── transforms.py             # pure functions, no I/O
│   │   ├── watermark.py
│   │   └── monitoring.py             # GHA job summary
│   └── models/
│       └── contact.py                # Contact dataclass
├── data/
│   ├── watermark.json                # committed after each run
│   └── watermark_debug.json          # used when DEBUG=true
├── main.py                           # async orchestrator
├── pyproject.toml
├── uv.lock
└── .env.example
```

### Environment Variables
```
AZURE_CLIENT_ID=        # Azure app registration
AZURE_TENANT_ID=        # Azure app registration
REFRESH_TOKEN=          # OAuth2 refresh token — long-lived, auto-renews
MONDAY_API_KEY=         # Monday profile → Administration → API
MONDAY_BOARD_ID=        # from board URL
GROQ_API_KEY=           # console.groq.com
DEBUG=                  # true/false — uses debug watermark, extra logging
```

### Groq Model Reference
- **Text extraction:** `llama-3.3-70b-versatile`
- **Vision (fallback):** `meta-llama/llama-4-scout-17b-16e-instruct`
- Free tier limits (text model): 30 RPM, 1K RPD, 12K TPM, 100K TPD
- Models deprecate frequently — keep model name as a config constant, not hardcoded

### Monday Column Value Formats (fiddly — easy to get wrong)
```python
email:     {"email": "a@b.com", "text": "a@b.com"}
phone:     {"phone": "+441234567890", "countryShortName": "GB"}
url/link:  {"url": "https://...", "text": "display"}
text:      "plain string"
status:    {"label": "Active"}
```

---

## Coding Preferences

### Style
- **Async-first** — `asyncio` + `aiohttp` for all IO-bound work
- **Type hints everywhere** — all function signatures, dataclass fields
- **Dataclasses over raw dicts** — never use dicts as function contracts
- **Pure transform functions** — `utils/transforms.py` has no side effects, no I/O
- **Private helpers with `_` prefix** — anything not part of the public interface
- **Explicit over clever** — readable beats concise when they conflict

### Error Handling
- Catch the narrowest exception possible — never bare `except Exception: pass`
- Per-item try/except in pipeline loops — log, skip, continue
- Always re-raise at the top level so GHA marks the job failed
- Return `None` or empty dict rather than raising for "not found" cases

### Logging
- `get_logger(__name__)` in every module
- `logger.debug` for data previews — always truncate: `text[:100]`
- `logger.info` for pipeline milestones
- `logger.warning` for skipped items
- `logger.exception` for unexpected errors — includes stack trace automatically
- Never use `print` in application code

### Retry Strategy
- **Always use tenacity** — never write manual retry loops
- **Groq:** `wait_exponential_jitter(initial=60, max=300, jitter=15)` — 60s matches TPM reset window
- **Jitter always** — prevents retry storms in batch processing
- **`before_sleep_log`** — essential for unattended GHA runs
- Retry on transient errors only: `RateLimitError`, `APIConnectionError`, `APITimeoutError`
- Graceful fallback when all retries fail — partial result with `_extraction_failed: True` flag

### Testing Preferences
- Pytest + pytest-asyncio for async tests
- Unit tests for pure transform functions — easy to test, no mocks needed
- Integration tests sparingly — they need real credentials

---

## Working Patterns

### General Approach
- **Cheap extraction first** — regex and local tools before API calls
- **Fail fast on config** — validate all env vars at startup, not at point of use
- **Log everything in CI** — unattended runs need verbose output to debug failures
- **One concern per module** — clients handle API calls, utils handle transforms, main orchestrates
- **Debug mode** — `DEBUG=true` uses separate watermark so test runs don't pollute production state

### Tool Preferences
- **uv** over pip — always
- **tenacity** over manual retry logic
- **phonenumbers library** over regex for phone extraction — handles international formats
- **BeautifulSoup** for HTML parsing — preserve `href` attributes, LinkedIn URLs hide in anchor tags
- **`response_format: json_object`** on all Groq calls — guarantees valid JSON back
- **`temperature=0`** on all extraction calls — determinism over creativity

### GHA Specifics
- `astral-sh/setup-uv@v4` for uv setup
- `uv run python main.py` to execute
- Tesseract: `sudo apt-get install -y tesseract-ocr && tesseract --version`
- Commit watermark back after each run with `git diff --staged --quiet || git commit`
- Write job summary to `$GITHUB_STEP_SUMMARY` for visibility in GHA UI
- `workflow_dispatch` always alongside `schedule` — allows manual trigger
- Historic mode via env flag — run once manually, then let scheduler handle ongoing

### What to Avoid
- Don't use `pip` — always `uv`
- Don't pass full email body to Groq — use signature tail only
- Don't silently swallow exceptions in pipeline loops — always log
- Don't hardcode model names — use a config constant
- Don't use `body` from Graph API — use `uniqueBody`
- Don't trust Groq to return valid JSON without `response_format: json_object`
- Don't store access tokens — always derive from refresh token at runtime

---

## Recent Improvements (April 26, 2026)

### Robustness Enhancements
- **Environment validation:** Added `_validate_env()` function that fails fast with clear error messages if required env vars missing
  - Tests: 7 comprehensive unit tests covering success case, individual missing vars, multiple missing vars, and error message validation
- **Exception handling fix:** Fixed bug where `outlook_contact` could be undefined in error handler
  - Now properly initialized as `Optional[Contact] = None` before try block
  - Only appended to skipped list if successfully created
- **Rate limit configuration:** Externalized hardcoded `15s` sleep into `RATE_LIMIT_DELAY_SEC` env var (default 15 seconds)

### Functionality Additions
- **CLI flags:** Added argparse with `--debug` and `--dry-run` flags
  - `--debug`: Enables verbose logging, overrides DEBUG env var
  - `--dry-run`: Previews changes without writing to Monday.com or updating watermark
- **Environment documentation:** Created `.env.example` with all required/optional vars and inline comments on credential sourcing

### Testing Coverage
- Created `test_main.py` with 7 tests for `_validate_env()` covering:
  - ✓ Success case with all required vars
  - ✓ Individual missing var errors (each of 4 required vars)
  - ✓ Multiple missing vars reported together
  - ✓ Error message validation (mentions `.env` file for guidance)
- All 251 existing tests pass; new test suite adds 7 more

### Code Quality Improvements
- ✓ Type hints: Added `Optional[Contact]` annotation in main loop
- ✓ Ruff lint: all checks pass
- ✓ Syntax validation: passes
- ✓ CLI help: displays correctly with `--help`

### Architecture Notes
- **Global `dry_run` variable:** Coordinates dry-run mode across function scope (set by CLI, checked before writes)
- **Early validation:** `_validate_env()` called before any async operations to fail fast
- **Test pattern:** Use `patch.dict(os.environ, {...}, clear=True/False)` for safe env var mocking in tests
