# DSPy Jira Feedback

A production-ready Python project using DSPy and Model Context Protocol (MCP) to automatically review Jira issues and provide actionable, rubric-driven feedback.

## Features

- 🤖 **AI-Powered Analysis**: Uses DSPy with configurable LLMs (GPT-4, Claude, etc.)
- 📊 **Rubric-Based Scoring**: Deterministic evaluation across 7+ criteria
- 💬 **Smart Feedback**: Post comments to Jira or generate grouped reports
- 🔄 **Idempotency**: SQLite cache prevents duplicate comments
- 🎯 **Configurable**: Extensive configuration via environment variables
- 📈 **Analytics**: Summary reports with score distributions
- 🔔 **Notifications**: Optional Slack webhooks for critical issues
- ✅ **Tested**: Comprehensive unit tests included

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Jira Cloud account with API access
- OpenAI API key (or other LLM provider)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/dspy-jira-feedback.git
cd dspy-jira-feedback

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
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
```

## Rubric Criteria

The system evaluates issues across these criteria:

1. **Title Clarity** - Clear, actionable, contains outcome
2. **Description Length** - Meets minimum word count
3. **Acceptance Criteria** - Present and testable
4. **Ambiguous Terms** - Avoids vague language (e.g., "optimize", "ASAP")
5. **Estimate Present** - Has story points or time estimate
6. **Labels** - Appropriate and valid labels
7. **Scope Clarity** - Well-defined scope and dependencies

Each criterion has a score (0-1) and weight. Final score is 0-100.

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
MODEL=gpt-4o-mini  # or gpt-3.5-turbo, claude-3-haiku-20240307
OPENAI_API_KEY=sk-...

# Rubric (optional)
MIN_DESCRIPTION_WORDS=20
REQUIRE_ACCEPTANCE_CRITERIA=true
ALLOWED_LABELS=bug,feature,enhancement
AMBIGUOUS_TERMS=optimize,ASAP,soon,quickly

# Notifications (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
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
        suggestion="How to improve",
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
## 🌟 Feedback for ABC-123

**Score:** 85/100

### Overall Assessment
Well-structured issue with clear objectives...

### ✅ Strengths
- Clear and actionable title
- Comprehensive description
- Testable acceptance criteria

### 🔧 Areas for Improvement
- Missing estimate
- Could clarify dependencies

### 💡 Actionable Suggestions
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

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_rubric.py -v
```

## Architecture

```
src/
  app.py              # CLI application & main entry point
  config.py           # Configuration management (Pydantic)
  jira_client.py      # Jira API wrapper (MCP-compatible)
  rubric.py           # Deterministic rubric evaluation
  signatures.py       # DSPy signatures for LLM tasks
  pipeline.py         # Main feedback generation pipeline
  cache.py            # SQLite idempotency cache
  feedback_writer.py  # Format and deliver feedback

tests/
  test_rubric.py      # Rubric evaluation tests
  test_cache.py       # Cache functionality tests
  test_pipeline.py    # Pipeline integration tests
```

### How It Works

1. **Query**: Fetch issues from Jira using JQL
2. **Filter**: Check cache to skip already-commented issues
3. **Evaluate**: Run deterministic rubric checks
4. **Analyze**: Use DSPy + LLM for qualitative feedback
5. **Format**: Generate markdown feedback
6. **Deliver**: Post as comment or append to report
7. **Cache**: Mark issue as processed

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
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .

      - name: Run feedback analysis
        env:
          JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          FEEDBACK_MODE: report
        run: |
          python -m src.app --limit 50

      - name: Upload report
        uses: actions/upload-artifact@v3
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
```

### Cache Issues

Reset cache:
```bash
python -m src.app --clear-cache
# Or manually delete: rm -rf .cache/
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Development Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run formatters
black src/ tests/
ruff check src/ tests/

# Run tests
pytest -v
```

## License

MIT License - see [LICENSE](LICENSE) file

## Acknowledgments

- Built with [DSPy](https://github.com/stanfordnlp/dspy)
- Designed for [Model Context Protocol](https://modelcontextprotocol.io/)
- Integrates with [Atlassian Jira](https://www.atlassian.com/software/jira)

## Support

- **Issues**: https://github.com/yourusername/dspy-jira-feedback/issues
- **Discussions**: https://github.com/yourusername/dspy-jira-feedback/discussions
- **Email**: your.email@example.com
