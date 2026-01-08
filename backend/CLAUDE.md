# CLAUDE.md

This file provides guidance to Claude Code when working with this codebase.

## Project: DSPy Jira Feedback

A production-ready Python system using DSPy and Model Context Protocol (MCP) for automated Jira issue analysis and feedback generation with rubric-driven scoring.

## Technology Stack

- **Language**: Python 3.11+
- **AI Framework**: DSPy (Stanford)
- **LLM**: OpenAI GPT-4o-mini (configurable)
- **API Integration**: Atlassian Jira REST API v3
- **Database**: SQLite (caching/idempotency)
- **Testing**: pytest
- **Dependencies**: pydantic, python-dotenv, rich, httpx

## Common Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -e .

# Run
python -m src.app --dry-run --limit 5    # Test run
python -m src.app --limit 10             # Post feedback
python -m src.app --stats                # View cache stats

# Development
pip install -e ".[dev]"                  # Install dev dependencies
pytest                                    # Run tests
pytest --cov=src                         # Run with coverage
black src/ tests/                        # Format code
ruff check src/ tests/                   # Lint code

# Configuration
cp .env.example .env                     # Create config
```

## Project Structure

```
src/
  app.py              # Main CLI application entry point
  config.py           # Pydantic configuration from environment
  jira_client.py      # Jira API wrapper (MCP-compatible)
  rubric.py           # Deterministic rubric evaluation rules
  signatures.py       # DSPy signatures for LLM tasks
  pipeline.py         # Feedback generation pipeline
  cache.py            # SQLite idempotency cache
  feedback_writer.py  # Feedback formatting and delivery

tests/
  test_rubric.py      # Rubric evaluation tests
  test_cache.py       # Cache functionality tests
  test_pipeline.py    # Pipeline integration tests

.env.example          # Template configuration
pyproject.toml        # Project metadata and dependencies
README.md             # User documentation
```

## Architecture Overview

### 1. Configuration Layer (config.py)
- Loads environment variables via `python-dotenv`
- Validates configuration with Pydantic models
- Supports both PAT and OAuth authentication
- Configurable rubric criteria

### 2. Jira Integration (jira_client.py)
- **MCP-Compatible**: Designed for easy MCP tool integration
- Wraps Jira REST API v3 calls
- Handles authentication (Basic Auth for PAT)
- Retry logic with exponential backoff
- Converts Markdown ↔ Atlassian Document Format (ADF)
- `JiraIssue` class normalizes issue data

### 3. Rubric System (rubric.py)
- **Deterministic evaluation** across 7 criteria:
  1. Title clarity
  2. Description length
  3. Acceptance criteria presence
  4. Ambiguous terms detection
  5. Estimate presence
  6. Label validation
  7. Scope clarity
- Each rule returns `RubricResult` with score (0-1) and suggestions
- Weighted scoring produces final 0-100 score

### 4. DSPy Pipeline (pipeline.py, signatures.py)
- **Signatures**:
  - `IssueCritique`: Qualitative analysis of issue
  - `AcceptanceCriteriaRefinement`: Improve AC formatting
- **Pipeline Flow**:
  1. Run rubric checks (deterministic)
  2. Format findings for LLM
  3. Call DSPy modules for critique/refinement
  4. Combine rubric + LLM outputs
  5. Generate final `Feedback` object

### 5. Caching (cache.py)
- SQLite-based idempotency tracking
- Stores content hash per issue
- Prevents duplicate comments
- Tracks comment count and timestamps
- Simple statistics API

### 6. Feedback Delivery (feedback_writer.py)
- **Comment mode**: Posts to Jira as formatted comments
- **Report mode**: Appends to daily markdown reports
- Generates summary reports with statistics
- Optional Slack notifications

### 7. CLI Application (app.py)
- Argparse-based command-line interface
- Orchestrates all components
- Rich console output with progress tracking
- Exit codes for CI integration (non-zero on critical issues)

## Key Patterns

### Error Handling
- All external API calls wrapped in try-except
- Graceful degradation (e.g., rubric-only feedback if LLM fails)
- Rich console logging for all operations

### Configuration
- All secrets in environment variables
- Pydantic validation at startup
- Type-safe configuration objects

### Testing
- Pytest with fixtures for test data
- Mock issue creation helpers
- Unit tests for each module
- Integration tests with mocked LLM calls

### Type Safety
- Full type hints throughout
- Pydantic models for validation
- Dataclasses for data transfer objects

## Environment Variables

Required:
- `JIRA_BASE_URL`: Jira instance URL
- `JIRA_EMAIL`: User email (for PAT auth)
- `JIRA_API_TOKEN`: API token
- `JQL`: Issue query
- `OPENAI_API_KEY`: LLM provider key

Optional:
- `FEEDBACK_MODE`: `comment` or `report` (default: `comment`)
- `MODEL`: LLM model name (default: `gpt-4o-mini`)
- `MIN_DESCRIPTION_WORDS`: Minimum description words (default: 20)
- `REQUIRE_ACCEPTANCE_CRITERIA`: Require AC (default: true)
- `ALLOWED_LABELS`: Comma-separated label allowlist
- `SLACK_WEBHOOK_URL`: Slack notifications

## Common Tasks

### Adding a New Rubric Rule

1. Edit src/rubric.py
2. Add method `_check_new_rule(self, issue: JiraIssue) -> RubricResult`
3. Add to `evaluate()` method
4. Write test in tests/test_rubric.py

### Changing Feedback Format

Edit src/feedback_writer.py:
- `_format_as_markdown()`: Markdown structure
- `_markdown_to_adf()`: Jira ADF conversion (in jira_client.py)

### Adding New DSPy Signature

1. Add to src/signatures.py
2. Create module in src/pipeline.py
3. Integrate into pipeline flow

### Enabling MCP Mode

Create `MCPJiraClient` subclass:
```python
class MCPJiraClient(JiraClient):
    def search_issues(self, jql, fields=None, **kwargs):
        return mcp.call_tool("jira", "search_issues", {
            "jql": jql,
            "fields": fields
        })
```

## Troubleshooting

### Tests Failing
- Ensure virtual environment is activated
- Install dev dependencies: `pip install -e ".[dev]"`
- Check Python version: `python --version` (needs 3.11+)

### Import Errors
- Run from project root, not `src/` directory
- Use `python -m src.app`, not `python src/app.py`

### LLM Rate Limits
- Reduce `--limit` parameter
- Add retry logic in `pipeline.py`
- Switch to different model provider

### Jira API Errors
- Verify API token is valid
- Check Jira permissions (need comment access)
- Test connection: `curl -u email:token https://domain.atlassian.net/rest/api/3/myself`

## Development Guidelines

1. **Type Safety**: Always add type hints
2. **Error Handling**: Catch specific exceptions, log clearly
3. **Testing**: Write tests for new features
4. **Documentation**: Update docstrings and README
5. **Configuration**: Add new settings to `.env.example`
6. **Logging**: Use `rich.console` for user-facing output

## Security

- Never commit `.env` files
- Store all secrets in environment variables
- Use secure token generation for webhooks
- Validate all external inputs
- Use parameterized queries (SQLite)

## Performance

- Cache prevents duplicate processing
- Batch issue fetching (max 50 per query)
- Lazy LLM calls (only when needed)
- SQLite for fast local caching

## Future Enhancements

- [ ] True MCP integration with tool calling
- [ ] Additional LLM providers (Anthropic, Cohere)
- [ ] Web UI for configuration/monitoring
- [ ] Webhook receiver mode (vs. polling)
- [ ] Multi-project support
- [ ] Custom rubric templates
- [ ] A/B testing for prompts
