# DSPy Jira Feedback

**Author:** Cristian Prodius

A production-ready Python project using DSPy and Model Context Protocol (MCP) to automatically review Jira issues and provide actionable, rubric-driven feedback.

## Features

- **AI-Powered Analysis**: Uses DSPy with configurable LLMs (GPT-4, Claude, etc.)
- **Rubric-Based Scoring**: Deterministic evaluation across 7+ criteria
- **Smart Feedback**: Post comments to Jira or generate grouped reports
- **Idempotency**: SQLite cache prevents duplicate comments
- **Thread-Safe**: Concurrent access support with proper locking
- **Configurable**: Extensive configuration via environment variables
- **Analytics**: Summary reports with score distributions
- **Notifications**: Optional Slack webhooks for critical issues
- **Security**: Input sanitization, on-demand credentials, prompt injection protection
- **Tested**: Comprehensive unit tests with 140+ test cases

## Architecture Overview

### System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DSPy Jira Feedback System                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────────┐
│  CLI     │────▶│   AppConfig  │────▶│ JiraClient  │────▶│   Jira Cloud     │
│ (app.py) │     │ (config.py)  │     │             │     │   REST API v3    │
└──────────┘     └──────────────┘     └─────────────┘     └──────────────────┘
     │                                       │
     │                                       ▼
     │                              ┌─────────────────┐
     │                              │   JiraIssue     │
     │                              │   (normalized)  │
     │                              └─────────────────┘
     │                                       │
     ▼                                       ▼
┌──────────────┐                    ┌─────────────────┐
│ FeedbackCache│◀──────────────────▶│ FeedbackPipeline│
│  (SQLite)    │                    │  (pipeline.py)  │
└──────────────┘                    └─────────────────┘
                                            │
                          ┌─────────────────┼─────────────────┐
                          ▼                 ▼                 ▼
                   ┌────────────┐   ┌─────────────┐   ┌─────────────┐
                   │  Rubric    │   │   DSPy      │   │   Input     │
                   │ Evaluator  │   │  Modules    │   │ Sanitizer   │
                   │(rubric.py) │   │(signatures) │   │ (security)  │
                   └────────────┘   └─────────────┘   └─────────────┘
                          │                 │
                          └────────┬────────┘
                                   ▼
                          ┌─────────────────┐
                          │    Feedback     │
                          │   (dataclass)   │
                          └─────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ FeedbackWriter  │
                          │                 │
                          └─────────────────┘
                           │               │
                           ▼               ▼
                    ┌───────────┐   ┌───────────┐
                    │   Jira    │   │  Report   │
                    │  Comment  │   │   File    │
                    └───────────┘   └───────────┘
```

### Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Request/Response Flow                            │
└─────────────────────────────────────────────────────────────────────────────┘

User Input                Processing                           Output
─────────                 ──────────                           ──────

$ python -m src.app
        │
        ▼
┌───────────────┐
│ Parse CLI Args│
│   --dry-run   │
│   --limit N   │
│   --project   │
└───────┬───────┘
        │
        ▼
┌───────────────┐    ┌─────────────┐
│ Load Config   │───▶│ Validate    │
│ from .env     │    │ Credentials │
└───────┬───────┘    └─────────────┘
        │
        ▼
┌───────────────┐    ┌─────────────┐    ┌─────────────────┐
│ Search Jira   │───▶│ Filter by   │───▶│ For Each Issue  │
│ (JQL Query)   │    │ Cache Hash  │    │                 │
└───────────────┘    └─────────────┘    └────────┬────────┘
                                                 │
                     ┌───────────────────────────┘
                     ▼
        ┌────────────────────────┐
        │   Pipeline Processing  │
        │                        │
        │  1. Rubric Evaluation  │──────▶ Deterministic Score
        │  2. Sanitize Input     │──────▶ Security Filter
        │  3. DSPy LLM Call      │──────▶ AI Critique
        │  4. Score Validation   │──────▶ 0-100 Range Check
        │  5. Build Feedback     │──────▶ Structured Output
        │                        │
        └───────────┬────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌───────────────┐       ┌───────────────┐
│ Comment Mode  │       │ Report Mode   │
│               │       │               │
│ POST to Jira  │       │ Write to File │
│ Update Cache  │       │ with Locking  │
└───────────────┘       └───────────────┘
        │                       │
        └───────────┬───────────┘
                    ▼
            ┌───────────────┐
            │ Summary Stats │──────▶ Console Output
            │ Slack Notify  │──────▶ Webhook (optional)
            └───────────────┘
```

### Pipeline Processing Detail

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Feedback Pipeline Flow                              │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │    JiraIssue     │
                    │                  │
                    │  - key           │
                    │  - title         │
                    │  - description   │
                    │  - acceptance    │
                    │  - estimate      │
                    │  - labels        │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Rubric Check 1  │ │ Rubric Check 2  │ │ Rubric Check N  │
│ Title Clarity   │ │ Description Len │ │ Scope Clarity   │
│                 │ │                 │ │                 │
│ Score: 0.0-1.0  │ │ Score: 0.0-1.0  │ │ Score: 0.0-1.0  │
│ Weight: 1.5     │ │ Weight: 1.0     │ │ Weight: 1.0     │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             ▼
                    ┌──────────────────┐
                    │ Weighted Average │
                    │                  │
                    │  Σ(score×weight) │
                    │  ─────────────── │
                    │     Σ(weight)    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Sanitize Input   │
                    │                  │
                    │ - Strip injections│
                    │ - Truncate length │
                    │ - Escape patterns │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  DSPy Module     │
                    │                  │
                    │  IssueCritique   │◀──── LLM (GPT-4/Claude)
                    │  AC Refinement   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Score Validate  │
                    │                  │
                    │  0 ≤ score ≤ 100 │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    Feedback      │
                    │                  │
                    │  - score         │
                    │  - strengths[]   │
                    │  - improvements[]│
                    │  - suggestions[] │
                    │  - improved_ac   │
                    │  - resources[]   │
                    └──────────────────┘
```

### Exception Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Exception Hierarchy                               │
└─────────────────────────────────────────────────────────────────────────────┘

Exception (builtin)
      │
      └──▶ JiraFeedbackError (base)
                  │
                  ├──▶ ConfigurationError
                  │         └── Invalid .env, missing required fields
                  │
                  ├──▶ JiraAPIError
                  │         │    └── status_code, issue_key attributes
                  │         │
                  │         ├──▶ JiraAuthenticationError (401)
                  │         │
                  │         └──▶ JiraRateLimitError (429)
                  │
                  ├──▶ CacheError
                  │         └── SQLite connection/query failures
                  │
                  └──▶ PipelineError
                            │
                            └──▶ LLMError
                                      └── DSPy/OpenAI/Claude failures

ValidationError (pydantic)
      │
      └──▶ ScoreValidationError
                  └── Score outside 0-100 range
```

### Data Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Data Models                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐      ┌─────────────────────┐      ┌──────────────────┐
│    JiraIssue        │      │    RubricResult     │      │    Feedback      │
├─────────────────────┤      ├─────────────────────┤      ├──────────────────┤
│ key: str            │      │ rule_id: str        │      │ issue_key: str   │
│ title: str          │      │ score: float (0-1)  │      │ score: float     │
│ description: str?   │      │ message: str        │      │ overall: str     │
│ acceptance: str?    │      │ suggestion: str?    │      │ strengths: []    │
│ estimate: float?    │      │ weight: float       │      │ improvements: [] │
│ labels: list[str]   │      └─────────────────────┘      │ suggestions: []  │
│ project: str        │                                   │ improved_ac: str?│
│ issue_type: str     │                                   │ resources: []    │
│ status: str         │                                   │ rubric_breakdown │
│ assignee: str?      │                                   └──────────────────┘
│ created: datetime   │
│ updated: datetime   │
├─────────────────────┤
│ content_hash() →str │  Hash of key fields for cache comparison
└─────────────────────┘

┌─────────────────────┐      ┌─────────────────────┐
│    AppConfig        │      │   JiraAuthConfig    │
├─────────────────────┤      ├─────────────────────┤
│ jira: JiraAuthConfig│      │ method: pat|oauth   │
│ jql: str            │      │ base_url: str       │
│ feedback_mode: str  │      │ email: str?         │
│ cache_db_path: Path │      │ api_token: str?     │
│ model: str          │      │ client_id: str?     │
│ openai_api_key: str?│      │ client_secret: str? │
│ anthropic_key: str? │      │ oauth_token: str?   │
│ rubric: RubricConfig│      └─────────────────────┘
│ slack_webhook: str? │
│ log_level: str      │
│ log_file: Path?     │
└─────────────────────┘
```

### Cache System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Cache System (SQLite)                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Table: comments                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  issue_key TEXT PRIMARY KEY     │  "ABC-123"                                │
│  content_hash TEXT              │  SHA256 of title+desc+AC+labels           │
│  comment_count INTEGER          │  Number of times commented                │
│  last_commented TIMESTAMP       │  Last feedback timestamp                  │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   Check Cache    │
                    │                  │
                    │ should_comment() │
                    └────────┬─────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                                 ▼
    ┌───────────────┐                ┌───────────────┐
    │ Not in cache  │                │ In cache but  │
    │ OR            │                │ same hash     │
    │ hash changed  │                │               │
    └───────┬───────┘                └───────┬───────┘
            │                                │
            ▼                                ▼
    ┌───────────────┐                ┌───────────────┐
    │   Process     │                │     Skip      │
    │   Issue       │                │   (no dupe)   │
    └───────────────┘                └───────────────┘

Thread Safety:
┌────────────────────────────────────────┐
│  threading.Lock() for all operations   │
│  WAL mode for concurrent reads         │
│  UPSERT for atomic check-and-mark      │
└────────────────────────────────────────┘
```

### Security Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Security Measures                                 │
└─────────────────────────────────────────────────────────────────────────────┘

1. Prompt Injection Protection
   ┌─────────────────────────────────────────────────────────────────────────┐
   │  User Input (Jira)     sanitize_llm_input()          LLM               │
   │  ─────────────────  ──────────────────────────▶  ─────────────         │
   │                                                                         │
   │  Patterns filtered:                                                     │
   │  - "ignore previous instructions"                                       │
   │  - "system:", "assistant:", "user:"                                     │
   │  - Delimiter injections: ```                                            │
   │  - Max length: 10,000 chars                                             │
   └─────────────────────────────────────────────────────────────────────────┘

2. On-Demand Credentials
   ┌─────────────────────────────────────────────────────────────────────────┐
   │  Email + Token        _get_auth_header()          HTTP Request         │
   │  ─────────────────  ──────────────────────────▶  ─────────────         │
   │                                                                         │
   │  - Base64 generated per-request                                         │
   │  - Not stored in memory long-term                                       │
   │  - Credentials never logged                                             │
   └─────────────────────────────────────────────────────────────────────────┘

3. Input Validation
   ┌─────────────────────────────────────────────────────────────────────────┐
   │  MAX_TITLE_LENGTH = 500                                                 │
   │  MAX_DESCRIPTION_LENGTH = 50000                                         │
   │  - Prevents memory exhaustion                                           │
   │  - Limits API payload size                                              │
   └─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Prerequisites

- Python 3.11+
- uv package manager (recommended) or pip
- Jira Cloud account with API access
- OpenAI API key (or Anthropic for Claude models)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/cristianprodius/dspy-jira-feedback.git
cd dspy-jira-feedback

# Using uv (recommended)
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e .

# Or using pip
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

### 3. Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Fill in your credentials:

```env
# Jira Configuration
JIRA_BASE_URL=https://yourcompany.atlassian.net
AUTH_METHOD=pat
JIRA_EMAIL=your.email@example.com
JIRA_API_TOKEN=your_api_token_here

# Query
JQL=project = ABC AND status in ("To Do","In Progress") ORDER BY updated DESC

# Feedback Mode
FEEDBACK_MODE=comment  # or 'report'

# LLM Configuration
MODEL=gpt-4o-mini
OPENAI_API_KEY=your_openai_key_here

# For Claude models (optional)
# MODEL=claude-3-haiku-20240307
# ANTHROPIC_API_KEY=your_anthropic_key_here

# Logging (optional)
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 4. Get API Credentials

**Jira API Token:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token to your `.env`

**OpenAI API Key:**
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy to your `.env`

**Anthropic API Key (for Claude):**
1. Go to https://console.anthropic.com/
2. Create a new API key
3. Copy to your `.env`

### 5. Run

```bash
# Dry run (print to console only)
python -m src.app --dry-run --limit 5

# Post actual feedback
python -m src.app --limit 10

# Generate report instead of comments
FEEDBACK_MODE=report python -m src.app --limit 20
```

## Usage

### Command Line Options

```bash
python -m src.app [OPTIONS]

Options:
  --once              Run once and exit (default)
  --dry-run          Print feedback to console, don't post to Jira
  --limit N          Limit number of issues to process
  --project ABC      Filter to specific project
  --clear-cache      Clear feedback cache before running
  --stats            Show cache statistics and exit
  --config FILE      Path to custom .env file
```

### Examples

```bash
# Analyze 5 issues and print feedback
python -m src.app --dry-run --limit 5

# Post feedback to issues in project XYZ
python -m src.app --project XYZ --limit 10

# Generate daily report
python -m src.app --limit 50
# Output: reports/YYYY-MM-DD_HHMM_report.md

# View cache statistics
python -m src.app --stats

# Clear cache and reprocess all
python -m src.app --clear-cache

# Use custom config file
python -m src.app --config production.env --limit 10
```

## Rubric Criteria

The system evaluates issues across these criteria:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Title Clarity | 1.5x | Clear, actionable, contains outcome |
| Description Length | 1.0x | Meets minimum word count (default: 20) |
| Acceptance Criteria | 1.5x | Present and testable |
| Ambiguous Terms | 1.0x | Avoids vague language (e.g., "optimize", "ASAP") |
| Estimate Present | 0.5x | Has story points or time estimate |
| Labels | 0.5x | Appropriate and valid labels |
| Scope Clarity | 1.0x | Well-defined scope and dependencies |

Each criterion scores 0.0-1.0. Final score is weighted average × 100.

## Configuration

### Environment Variables

```env
# Jira Settings
JIRA_BASE_URL=https://company.atlassian.net
AUTH_METHOD=pat  # or oauth
JIRA_EMAIL=user@example.com
JIRA_API_TOKEN=token

# Query
JQL=project = MYPROJ AND status != Done

# Feedback
FEEDBACK_MODE=comment  # or report
CACHE_DB_PATH=./.cache/jira_feedback.sqlite

# Model
MODEL=gpt-4o-mini  # or claude-3-haiku-20240307, gpt-4o
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...  # For Claude models

# Rubric (optional)
MIN_DESCRIPTION_WORDS=20
REQUIRE_ACCEPTANCE_CRITERIA=true
ALLOWED_LABELS=bug,feature,enhancement
AMBIGUOUS_TERMS=optimize,ASAP,soon,quickly

# Logging (optional)
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/app.log

# Notifications (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-1001234567890
```

### Telegram Notifications

To receive notifications via Telegram:

1. **Create a bot:**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow the prompts
   - Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Get your Chat ID:**
   - For personal notifications: Message [@userinfobot](https://t.me/userinfobot) to get your user ID
   - For group notifications: Add the bot to a group, then use the Telegram API to get the group chat ID
   - For channel notifications: Add the bot as admin to a channel, use `@channelusername` or the numeric ID

3. **Configure environment:**
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=-1001234567890
   ```

### Rubric Customization

Edit `src/rubric.py` to modify evaluation rules:

```python
def _check_custom_rule(self, issue: JiraIssue) -> RubricResult:
    # Your custom logic here
    return RubricResult(
        rule_id="custom_rule",
        score=1.0,
        message="Rule check message",
        suggestion=None,  # Optional suggestion
        weight=1.0
    )
```

Then add to `evaluate()` method:

```python
def evaluate(self, issue: JiraIssue) -> list[RubricResult]:
    results = []
    results.append(self._check_custom_rule(issue))
    # ... other checks
    return results
```

## Feedback Modes

### Comment Mode (`FEEDBACK_MODE=comment`)

Posts feedback directly to Jira issues as comments:

```markdown
## Feedback for ABC-123

**Score:** 85/100

### Overall Assessment
Well-structured issue with clear objectives...

### Strengths
- Clear and actionable title
- Comprehensive description
- Testable acceptance criteria

### Areas for Improvement
- Missing estimate
- Could clarify dependencies

### Actionable Suggestions
1. Add story points estimate
2. List any blocking issues
...
```

### Report Mode (`FEEDBACK_MODE=report`)

Generates markdown reports grouped by date:

```
reports/
  2025-01-15_1430_report.md      # Individual feedback
  2025-01-15_1430_summary.md     # Statistics summary
```

## Testing

Run the test suite:

```bash
# Install dev dependencies
pip install -e ".[dev]"
# Or with uv
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_rubric.py -v

# Run with verbose output
pytest -v --tb=short
```

Test coverage includes:
- Unit tests for rubric evaluation
- Cache functionality tests
- Pipeline integration tests
- Configuration validation tests
- Feedback writer tests
- Jira client tests
- Exception hierarchy tests
- Error handling tests

## Project Structure

```
src/
  app.py              # CLI application & main entry point
  config.py           # Configuration management (Pydantic)
  jira_client.py      # Jira API wrapper (MCP-compatible)
  rubric.py           # Deterministic rubric evaluation
  signatures.py       # DSPy signatures for LLM tasks
  pipeline.py         # Main feedback generation pipeline
  cache.py            # SQLite idempotency cache (thread-safe)
  feedback_writer.py  # Format and deliver feedback
  exceptions.py       # Custom exception hierarchy
  logging_config.py   # Structured logging configuration

tests/
  conftest.py         # Shared pytest fixtures
  test_rubric.py      # Rubric evaluation tests
  test_cache.py       # Cache functionality tests
  test_pipeline.py    # Pipeline integration tests
  test_config.py      # Configuration tests
  test_feedback_writer.py  # Feedback writer tests
  test_jira_client.py # Jira client tests
  test_exceptions.py  # Exception tests
```

## MCP Integration

The codebase is designed for MCP (Model Context Protocol) integration. The `JiraClient` class wraps all Jira operations and can be easily adapted to use MCP tool calls:

```python
# Current (direct API)
response = self.client.request("GET", f"{base_url}/search", params=...)

# MCP mode (future)
response = mcp.call_tool("jira", "search_issues", {"jql": jql, "fields": fields})
```

To enable MCP mode, implement an `MCPJiraClient` subclass that overrides the request methods.

## CI/CD

### GitHub Actions Example

Create `.github/workflows/feedback.yml`:

```yaml
name: Nightly Jira Feedback

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily
  workflow_dispatch:

jobs:
  feedback:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: |
          uv venv
          uv pip install -e .

      - name: Run feedback analysis
        env:
          JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          FEEDBACK_MODE: report
        run: |
          source .venv/bin/activate
          python -m src.app --limit 50

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: feedback-report
          path: reports/*.md
```

## Troubleshooting

### No Issues Found

Check your JQL query:
```bash
# Test JQL directly in Jira
# https://yourcompany.atlassian.net/issues/?jql=YOUR_JQL_HERE
```

### Authentication Failed

Verify credentials:
```bash
# Test Jira connection
curl -u "email:token" https://yourcompany.atlassian.net/rest/api/3/myself
```

### LLM Errors

Check API key and model availability:
```bash
# Verify OpenAI key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Verify Anthropic key
curl https://api.anthropic.com/v1/models \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

### Cache Issues

Reset cache:
```bash
python -m src.app --clear-cache
# Or manually delete: rm -rf .cache/
```

### Import Errors

- Run from project root, not `src/` directory
- Use `python -m src.app`, not `python src/app.py`
- Ensure virtual environment is activated

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Development Setup

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run formatters
black src/ tests/
ruff check src/ tests/

# Run tests
pytest -v

# Run tests with coverage
pytest --cov=src --cov-report=term-missing
```

## License

MIT License - see [LICENSE](LICENSE) file

## Acknowledgments

- Built with [DSPy](https://github.com/stanfordnlp/dspy)
- Designed for [Model Context Protocol](https://modelcontextprotocol.io/)
- Integrates with [Atlassian Jira](https://www.atlassian.com/software/jira)

## Support

- **Issues**: https://github.com/cristianprodius/dspy-jira-feedback/issues
- **Author**: Cristian Prodius
