---
name: markdown
description: >
  Writing high-quality Markdown documents, especially README files for software projects.
  Use this skill whenever writing or reviewing a README, CHANGELOG, MEMORY, SKILL, ADR,
  or any other Markdown documentation file. Covers structure, tone, formatting rules,
  badge setup, and what to include or omit to make documentation clear and professional.
---

# Markdown Skill

## Core Philosophy

- **Write for the reader who knows nothing** — assume no context, explain the why not just the what
- **Design decisions over feature lists** — what you chose and why is more valuable than what it does
- **Show, don't tell** — code examples, diagrams, and badges over prose descriptions
- **Earn every section** — if a section adds no value, cut it
- **Tone is professional but human** — not academic, not casual; clear and direct

---

## README Structure

A good README answers these questions in order:

```
1. What is this?          — one sentence, top of file
2. Why does it exist?     — the problem it solves
3. How does it work?      — architecture, not code
4. How do I set it up?    — concrete steps
5. Why was it built this way? — design decisions
6. How do I contribute?   — if open source
```

### Template

```markdown
# project-name

> One sentence that says what it does and who it's for.

[![CI](https://github.com/user/repo/actions/workflows/ci.yml/badge.svg)](...)
[![codecov](https://codecov.io/gh/user/repo/badge.svg)](...)

## Overview
2-3 sentences expanding on the tagline. What problem does this solve?
What would someone have to do manually without it?

## How It Works

[Architecture diagram or pipeline description here]

\`\`\`mermaid
flowchart LR
    A[Source] --> B[Process] --> C[Destination]
\`\`\`

Brief prose walking through the diagram.

## Stack

| Component | Technology | Why |
|---|---|---|
| Email source | Microsoft Graph API | Outlook 365 access |
| AI extraction | Groq (free tier) | Zero cost for this volume |
| OCR | Tesseract | Local, free, no API dependency |
| CRM | Monday.com | Existing tool |
| CI/CD | GitHub Actions | Free, integrated |

## Setup

### Prerequisites
- Python 3.11+
- uv
- Azure account (free tier sufficient)

### Installation

\`\`\`bash
git clone https://github.com/you/project
cd project
uv sync
cp .env.example .env
# fill in .env values — see below
\`\`\`

### Environment Variables

| Variable | Where to get it |
|---|---|
| `AZURE_CLIENT_ID` | Azure portal → App registrations |
| `REFRESH_TOKEN` | Run `uv run python scripts/get_refresh_token.py` once |
| `MONDAY_API_KEY` | Monday → Profile → Administration → API |
| `GROQ_API_KEY` | console.groq.com |

### Running Locally

\`\`\`bash
uv run python main.py
\`\`\`

## Design Decisions

**Why Groq over OpenAI**
Free tier handles the volume comfortably. Model names deprecate periodically
so the model is kept as a config constant for easy swapping.

**Why Tesseract before Groq vision**
Local OCR costs nothing and handles most signature images adequately.
Groq vision only fires when OCR returns nothing useful — minimises API calls.

**Why watermark pattern instead of a database**
A JSON file committed back to the repo after each run is simpler, free,
and sufficient. No database to provision, back up, or pay for.

**Why trusted sender filter**
Only processing emails from addresses we have previously contacted prevents
newsletters, spam, and auto-replies from polluting the CRM.
```

---

## Badges

Badges go immediately after the title and tagline, before any prose.
Keep to 3 or fewer — more than that looks cluttered.

### CI Badge (free, no setup)
```markdown
[![CI](https://github.com/USER/REPO/actions/workflows/WORKFLOW.yml/badge.svg)](https://github.com/USER/REPO/actions/workflows/WORKFLOW.yml)
```

### Codecov Badge
```markdown
[![codecov](https://codecov.io/gh/USER/REPO/badge.svg)](https://codecov.io/gh/USER/REPO)
```

### Python Version
```markdown
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
```

### License
```markdown
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
```

---

## Architecture Diagrams

Use Mermaid — renders natively in GitHub, no image files needed.

### Pipeline / Flow
```markdown
\`\`\`mermaid
flowchart LR
    A[Outlook Inbox] -->|Graph API| B[Filter]
    B --> C[Extract]
    C --> D{Exists?}
    D -->|No| E[Create]
    D -->|Yes| F[Update]
    E --> G[Monday.com]
    F --> G
\`\`\`
```

### System Architecture
```markdown
\`\`\`mermaid
graph TD
    A[GitHub Actions] -->|triggers| B[main.py]
    B --> C[OutlookClient]
    B --> D[MondayClient]
    C -->|emails| E[Extractor]
    E -->|contacts| D
\`\`\`
```

### Sequence
```markdown
\`\`\`mermaid
sequenceDiagram
    GHA->>Outlook: fetch inbox
    Outlook-->>GHA: emails
    GHA->>Groq: extract contact
    Groq-->>GHA: structured data
    GHA->>Monday: create/update
\`\`\`
```

Keep diagrams simple — if it needs a legend to understand, simplify it.

---

## Design Decisions Section

This is the most valuable section for technical readers and employers.
It shows deliberate engineering thinking, not just ability to make things work.

### Format Per Decision

```markdown
**Why [choice] over [alternative]**
One or two sentences. Context → Decision → Consequence.
No bullet points — prose reads better for reasoning.
```

### What Makes a Good Design Decision Entry
- Names the alternative that was considered
- Explains the tradeoff, not just the choice
- Is honest about downsides ("model names deprecate periodically")
- Is concise — 2-4 sentences maximum

### What to Avoid
- "We chose X because it's better" — not a decision, it's a preference
- Explaining what the technology is — link to docs instead
- More than 6-7 decisions — pick the ones that weren't obvious

---

## CHANGELOG.md

Keep a running log of meaningful changes. Use reverse chronological order.
Not every commit needs an entry — only changes that affect behaviour.

```markdown
# Changelog

## 2024-02-01
- Added Tesseract OCR fallback for image-based email signatures
- Fixed signature extraction for out-of-office replies with no separator line

## 2024-01-15
- Switched Groq model to `llama-3.3-70b-versatile` after deprecation of 90b preview
- Added "Best wishes," to signature separator patterns

## 2024-01-10
- Initial release
```

---

## ADR Format (Architecture Decision Records)

```markdown
# 001 — [Decision Title]

## Status
Accepted | Superseded by [002] | Deprecated

## Context
What situation forced this decision? What constraints existed?

## Decision
What was chosen and why.

## Consequences
What becomes easier? What becomes harder? Any known downsides?
```

File naming: `docs/decisions/001-groq-over-openai.md`
Number sequentially — never reuse or delete numbers, only supersede.

---

## SKILL.md Format

```markdown
---
name: skill-name
description: >
  One paragraph. When to use this skill. What technologies/tasks it covers.
  Written so an AI agent can decide whether to load it based on the task.
---

# Skill Title

## Overview
What this covers and why it exists as a skill.

## [Topic]
Concrete patterns, code examples, gotchas.

---

## Common Errors
| Error | Cause | Fix |
```

The `description` frontmatter is the most important part — it's what determines
whether the skill gets loaded. Make it specific and task-oriented.

---

## Formatting Rules

### Headers
- `#` — document title only, one per file
- `##` — major sections
- `###` — subsections
- Never skip levels (no `#` then `###`)
- No trailing punctuation on headers

### Code Blocks
Always specify the language for syntax highlighting:
````markdown
```python
```yaml
```bash
```json
```markdown
````

Inline code for: file names, variable names, commands, values
```markdown
Run `uv sync` to install dependencies.
The `GROQ_API_KEY` environment variable is required.
```

### Tables
Use for comparisons, options, environment variables, error references.
Not for sequential steps — use numbered lists for those.

```markdown
| Column 1 | Column 2 | Column 3 |
|---|---|---|
| value    | value    | value    |
```

### Lists
- Bullet lists for unordered items — features, considerations, options
- Numbered lists for sequential steps — setup instructions, processes
- Never use bullet lists for things that have a natural order
- Keep list items parallel in structure and roughly equal in length

### Emphasis
- **Bold** for important terms, key decisions, warnings
- `code` for anything technical — commands, variables, file names, values
- Use sparingly — if everything is emphasised, nothing is

### Line Length
Wrap prose at 80-100 characters where possible. Keeps diffs readable.
Code blocks and tables are exempt.

---

## What to Omit

These sections add noise without value — leave them out unless genuinely needed:

- **"Getting Started"** as a header — just call it "Setup"
- **"Introduction"** — the overview paragraph IS the introduction
- **"Conclusion"** — documents don't need conclusions
- **"Feel free to..."** — just say what to do
- **Apologies for anything** — "this is a work in progress", "sorry for the mess"
- **Redundant badges** — don't badge every possible thing
- **Huge dependency lists** — link to `pyproject.toml` instead
- **Obvious instructions** — "click the button" level detail

---

## Tone Rules

- Write in present tense: "The pipeline fetches emails" not "The pipeline will fetch emails"
- Use active voice: "Groq extracts the contact" not "The contact is extracted by Groq"
- Address the reader as "you" in setup sections
- No exclamation marks — let the work speak
- No filler phrases: "It's worth noting that", "As mentioned above", "In order to"
- Be specific: "processes up to 166 emails/day on the free tier" beats "handles reasonable volume"

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| README describes features, not purpose | Lead with the problem it solves |
| No design decisions section | Add one — it's the most valuable section |
| Setup instructions skip prerequisites | List everything needed before step 1 |
| Architecture described in prose only | Add a Mermaid diagram |
| Badges broken or pointing to wrong branch | Check URLs render correctly after pushing |
| CHANGELOG missing | Start one now, even if just "Initial release" |
| Jargon without explanation | Link to docs or add a one-line explanation |
| Wall of text with no visual breaks | Break with headers, tables, code blocks |
