---
name: python
description: >
  Expert Python guidance covering code generation, debugging, architecture, and best practices.
  Use this skill whenever the user wants to write, review, refactor, or debug Python code —
  including async patterns, API integrations, data processing pipelines, CLI tools, testing,
  packaging, and CI/CD workflows like GitHub Actions. Also trigger for questions about Python
  libraries, project structure, environment setup, or anything involving .py files.
---

# Python Skill

## Core Philosophy

- **Explicit over implicit** — clear variable names, obvious control flow, no magic
- **Fail loudly** — raise meaningful exceptions early, never silently swallow errors
- **One responsibility per function** — if you need "and" to describe what it does, split it
- **Type hints everywhere** — they are documentation that the interpreter can check
- **Log, don't print** — use the `logging` module; `print` is for scripts, not applications

---

## Project Structure

```
project/
├── src/
│   ├── clients/        # External API clients (Outlook, Monday, Groq etc.)
│   ├── utils/          # Shared helpers (logger, retry, transforms)
│   └── models/         # Dataclasses / Pydantic models
├── tests/
│   ├── unit/
│   └── integration/
├── .github/
│   └── workflows/
├── .env.example        # Document all env vars here — never commit .env
├── main.py
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Environment Variables

Always load via `python-dotenv`. Never hardcode secrets.

```python
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MY_API_KEY")
DEBUG = os.getenv("DEBUG", "False").strip().lower() in {"true", "1", "yes"}
```

Validate at startup, not at point of use:

```python
def _validate_env() -> None:
    required = ["AZURE_CLIENT_ID", "MONDAY_API_KEY", "GROQ_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise EnvironmentError(f"Missing required env vars: {missing}")
```

---

## Logging

Use a shared logger factory — never configure logging in library code.

```python
# utils/logger.py
import logging

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG if os.getenv("DEBUG") else logging.INFO)
    return logger
```

Usage:
```python
from utils.logger import get_logger
logger = get_logger(__name__)

logger.info("Processing started")
logger.debug(f"Payload: {data[:100]}")   # truncate large payloads
logger.warning(f"Skipping {item}: {reason}")
logger.exception(f"Unexpected error")    # includes stack trace automatically
```

---

## Type Hints

```python
from typing import Optional

# Always hint function signatures
def parse_contact(email: dict, sender: str) -> Optional[Contact]:
    ...

# Use | for union types (Python 3.10+)
def get_value(key: str) -> str | None:
    ...

# Collections
from typing import List, Dict
def process_items(items: list[dict]) -> list[str]:
    ...
```

Use `dataclasses` or `pydantic` for structured data — never raw dicts as function contracts:

```python
from dataclasses import dataclass, field

@dataclass
class Contact:
    email_address: str
    name: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    job_title: str | None = None
    website: str | None = None
    address: str | None = None
    monday_id: str | None = None
```

---

## Async Patterns

Use `asyncio` for IO-bound work (API calls, network). Never mix sync and async carelessly.

```python
import asyncio
import aiohttp

# Concurrent execution — run independent tasks together
results = await asyncio.gather(
    client.get_inbox(),
    client.get_sent(),
)

# Context managers for clients that hold connections
async with MyClient() as client:
    data = await client.fetch()

# Rate limiting between async calls
await asyncio.sleep(1.0)  # be explicit about why if not obvious
```

Async client pattern:

```python
class MyClient:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self._api_key}"}
        )
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()
```

---

## Error Handling

**Be specific** — catch the narrowest exception possible:

```python
# Bad
try:
    result = do_thing()
except Exception:
    pass

# Good
try:
    result = do_thing()
except ValueError as e:
    logger.warning(f"Bad input: {e}")
    return None
except httpx.TimeoutError:
    logger.error("Request timed out")
    raise
```

**Pipeline resilience** — one bad item should never crash the whole run:

```python
for item in items:
    try:
        result = process(item)
    except Exception as e:
        logger.warning(f"Skipping {item.id}: {e}")
        skipped.append(item)
        continue
```

**Always re-raise** at the top level so GHA marks the job as failed:

```python
async def main():
    try:
        await run_pipeline()
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        raise  # ← GHA needs this to register failure
```

---

## Retry Strategy

Use `tenacity` for all external API calls. Never write manual retry loops.

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

def groq_retry_strategy(func):
    """
    Retry decorator for Groq API calls.
    - Exponential backoff with jitter to avoid retry storms
    - Initial wait of 60s matches Groq's TPM reset window
    - Catches transient errors only
    """
    from groq import RateLimitError, APIConnectionError, APITimeoutError
    return retry(
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
        wait=wait_exponential_jitter(initial=60, max=300, jitter=15),
        stop=stop_after_attempt(4),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
    )(func)
```

Apply as a decorator:

```python
@groq_retry_strategy
def call_groq(prompt: str) -> dict:
    ...
```

---

## Groq Integration

```python
import json
import os
from groq import Groq

GROQ_MODEL = "llama-3.3-70b-versatile"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@groq_retry_strategy
def extract_contact_fields(text: str, sender_email: str) -> dict:
    """
    Extract contact fields from email signature text.
    Uses json_object response format to guarantee valid JSON.
    temperature=0 for deterministic extraction.
    """
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{
            "role": "user",
            "content": f"""Extract contact info from this email signature.
Return ONLY valid JSON, null for anything not present:
{{"name":null,"phone":null,"linkedin_url":null,"job_title":null,"website":null,"address":null}}

Sender email (known): {sender_email}
EMAIL: {text}"""
        }],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content) or {}
```

**Token efficiency rules:**
- Pass only the signature tail, not the full email body
- Keep prompts under 200 words
- Set `max_tokens` on responses where output is bounded (e.g. JSON extractions: 200)
- Add `await asyncio.sleep(15)` between calls in batch loops on the free tier

---

## Data Transforms

Pure functions only — no side effects, no I/O:

```python
# utils/transforms.py

def get_sent_recipient_emails(sent_items: list[dict]) -> set[str]:
    """Extract unique recipient emails from sent items."""
    emails = set()
    for item in sent_items:
        for recipient in item.get("toRecipients", []):
            addr = recipient.get("emailAddress", {}).get("address", "")
            if addr:
                emails.add(addr.lower())
    return emails


def filter_inbox(inbox: list[dict], trusted: set[str]) -> list[dict]:
    """Keep only emails from addresses we have sent to."""
    return [
        email for email in inbox
        if _get_sender_email(email).lower() in trusted
    ]


def deduplicate_inbox(emails: list[dict]) -> list[dict]:
    """One email per sender address — most recent wins."""
    seen: dict[str, dict] = {}
    for email in emails:
        addr = _get_sender_email(email).lower()
        if addr not in seen:
            seen[addr] = email
    return list(seen.values())
```

---

## GitHub Actions

### Workflow template

```yaml
name: Sync Contacts

on:
  schedule:
    - cron: '0 * * * *'   # every hour
  workflow_dispatch:        # manual trigger from GitHub UI

jobs:
  sync:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync

      - name: Install Tesseract
        run: |
          sudo apt-get install -y tesseract-ocr
          tesseract --version      # fail fast if install went wrong

      - name: Run sync
        env:
          AZURE_CLIENT_ID:     ${{ secrets.AZURE_CLIENT_ID }}
          REFRESH_TOKEN:       ${{ secrets.REFRESH_TOKEN }}
          MONDAY_API_KEY:      ${{ secrets.MONDAY_API_KEY }}
          MONDAY_BOARD_ID:     ${{ secrets.MONDAY_BOARD_ID }}
          GROQ_API_KEY:        ${{ secrets.GROQ_API_KEY }}
        run: uv run python main.py

      - name: Commit watermark
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add data/watermark.json
          git diff --staged --quiet || git commit -m "chore: update watermark"
          git push
```

### Secrets

Store all keys in **Repo → Settings → Secrets and variables → Actions**. Never hardcode or log them. Access via `os.getenv()` only.

### Job summary output

Write a markdown summary visible in the GHA UI:

```python
# utils/monitoring.py
import os

def write_job_summary(created: int, updated: int, skipped: int, since: str) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return  # not running in GHA
    with open(summary_path, "a") as f:
        f.write(f"## Sync Complete\n")
        f.write(f"| Status | Count |\n|---|---|\n")
        f.write(f"| ✅ Created | {created} |\n")
        f.write(f"| 🔄 Updated | {updated} |\n")
        f.write(f"| ⏭️ Skipped | {skipped} |\n")
        f.write(f"\nProcessed emails since: `{since}`\n")
```

---

## Watermarking (Incremental Processing)

Track the last successful run timestamp to avoid reprocessing:

```python
# utils/watermark.py
import json
import os
from datetime import datetime, timezone

WATERMARK_PATH = "data/watermark.json"
DEBUG_WATERMARK_PATH = "data/watermark_debug.json"

def get_watermark(debug: bool = False) -> str | None:
    path = DEBUG_WATERMARK_PATH if debug else WATERMARK_PATH
    try:
        with open(path) as f:
            return json.load(f).get("since")
    except FileNotFoundError:
        return None  # first run — process everything

def update_watermark(debug: bool = False) -> None:
    path = DEBUG_WATERMARK_PATH if debug else WATERMARK_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"since": datetime.now(timezone.utc).isoformat()}, f)
```

---

## Common Patterns Quick Reference

```python
# Safe dict access with fallback
value = data.get("key", {}).get("nested", "default")

# Filter + transform in one
results = [transform(x) for x in items if condition(x)]

# Merge dicts, right side wins
merged = {**base_dict, **override_dict}

# First non-null value from multiple sources
value = next((v for v in [source1, source2, source3] if v), None)

# Truncate for logging
logger.debug(f"Body preview: {text[:100]}...")

# Boolean env var
DEBUG = os.getenv("DEBUG", "False").strip().lower() in {"true", "1", "yes"}

# Ensure directory exists before writing
os.makedirs(os.path.dirname(path), exist_ok=True)
```

---

## pyproject.toml Conventions

Pin major versions, allow minor/patch. uv manages the lockfile automatically.

```toml
[project]
name = "your-project"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "aiohttp>=3.9,<4.0",
    "beautifulsoup4>=4.12,<5.0",
    "groq>=0.9,<1.0",
    "phonenumbers>=8.13,<9.0",
    "pillow>=10.0,<11.0",
    "pytesseract>=0.3,<1.0",
    "python-dotenv>=1.0,<2.0",
    "tenacity>=8.2,<9.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]
```

Key uv commands:
```bash
uv sync                  # install all dependencies from lockfile
uv add <package>         # add a new dependency
uv run python main.py    # run within the uv-managed environment
uv run pytest            # run tests
```
