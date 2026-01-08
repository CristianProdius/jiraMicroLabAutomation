# Migration Complete: Next.js → DSPy Python

## Summary

The codebase has been **completely rebuilt** from a Next.js/TypeScript web application to a production-ready Python CLI tool using **DSPy** and **Model Context Protocol (MCP)** architecture.

## What Changed

### Before (Next.js)
- **Type**: Webhook-based web service
- **Stack**: Next.js 14, TypeScript, Vercel Postgres
- **Deployment**: Vercel serverless functions
- **UI**: React dashboard for viewing feedback
- **Mode**: Passive (waits for Jira webhooks)

### After (Python DSPy)
- **Type**: CLI tool / scheduled job
- **Stack**: Python 3.11+, DSPy, SQLite
- **Deployment**: Any Python environment, CI/CD, cron
- **UI**: Rich terminal output, Markdown reports
- **Mode**: Active (queries Jira on demand)

## New Architecture

### Core Components

1. **[src/config.py](src/config.py)** - Pydantic-based configuration
2. **[src/jira_client.py](src/jira_client.py)** - MCP-compatible Jira wrapper
3. **[src/rubric.py](src/rubric.py)** - 7 deterministic evaluation criteria
4. **[src/signatures.py](src/signatures.py)** - DSPy signatures for LLM tasks
5. **[src/pipeline.py](src/pipeline.py)** - Feedback generation orchestration
6. **[src/cache.py](src/cache.py)** - SQLite idempotency cache
7. **[src/feedback_writer.py](src/feedback_writer.py)** - Multi-format output
8. **[src/app.py](src/app.py)** - CLI application

### Key Features

✅ **Rubric-Based Scoring**: 7 deterministic criteria with weighted scores (0-100)
✅ **DSPy Integration**: LLM-powered qualitative analysis
✅ **Dual Output Modes**: Post comments to Jira OR generate reports
✅ **Idempotency**: SQLite cache prevents duplicate feedback
✅ **MCP-Ready**: Architecture prepared for MCP tool integration
✅ **Comprehensive Testing**: Unit tests for all modules
✅ **CLI**: Full command-line interface with rich output
✅ **CI/CD Ready**: Exit codes, report artifacts, dry-run mode

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your credentials

# Verify setup
./setup_check.sh
```

## Configuration Required

Update `.env` with:

```env
# Jira
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@example.com
JIRA_API_TOKEN=your_jira_api_token

# Query (customize for your project)
JQL=project = ABC AND status in ("To Do","In Progress")

# LLM
MODEL=gpt-4o-mini
OPENAI_API_KEY=your_openai_key

# Behavior
FEEDBACK_MODE=comment  # or 'report'
```

## Quick Start

```bash
# Dry run (test without posting)
python -m src.app --dry-run --limit 5

# Analyze and post feedback
python -m src.app --limit 10

# Generate report instead
FEEDBACK_MODE=report python -m src.app --limit 20

# View cache statistics
python -m src.app --stats
```

## Usage Patterns

### 1. Manual Ad-Hoc Analysis
```bash
python -m src.app --project XYZ --limit 10
```

### 2. Scheduled Daily Job (Cron)
```bash
# Add to crontab
0 9 * * * cd /path/to/project && python -m src.app --limit 50
```

### 3. CI/CD Pipeline (GitHub Actions)
See [README.md](README.md) for GitHub Actions workflow example.

### 4. Report Generation
```bash
python -m src.app --limit 100
# Output: reports/YYYY-MM-DD_HHMM_report.md
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_rubric.py -v
```

## Rubric Criteria

The system evaluates each issue on:

1. **Title Clarity** (weight: 1.0) - Actionable, clear, contains outcome
2. **Description Length** (weight: 1.2) - Meets minimum word count (default: 20)
3. **Acceptance Criteria** (weight: 1.5) - Present and testable
4. **Ambiguous Terms** (weight: 1.0) - Avoids vague language
5. **Estimate** (weight: 0.8) - Has story points or time
6. **Labels** (weight: 0.7) - Valid and appropriate
7. **Scope Clarity** (weight: 1.0) - Well-defined boundaries

**Final Score**: Weighted average × 100 (0-100 scale)

## Feedback Output

### Comment Mode
Posts structured feedback to Jira:

```markdown
## 🌟 Feedback for ABC-123
**Score:** 85/100

### Overall Assessment
Well-structured issue with clear objectives...

### ✅ Strengths
- Clear and actionable title
- Comprehensive description

### 🔧 Areas for Improvement
- Missing estimate
- Vague scope

### 💡 Actionable Suggestions
1. Add story points estimate
2. Define dependencies
...
```

### Report Mode
Generates timestamped Markdown files:
- `reports/YYYY-MM-DD_HHMM_report.md` - Individual feedback
- `reports/YYYY-MM-DD_HHMM_summary.md` - Statistics

## Migration Notes

### What Was Removed
- ❌ Next.js app/ directory
- ❌ React components
- ❌ Vercel deployment config
- ❌ Webhook handler
- ❌ Dashboard UI
- ❌ Vercel Postgres database
- ❌ Node.js dependencies

### What Was Retained (Conceptually)
- ✅ Rubric-based evaluation logic
- ✅ Jira API integration
- ✅ OpenAI feedback generation
- ✅ Feedback storage (now SQLite cache)
- ✅ Security best practices
- ✅ Configuration via environment

### What's New
- ✅ DSPy framework for LLM orchestration
- ✅ CLI application
- ✅ MCP-compatible architecture
- ✅ Dual output modes (comment/report)
- ✅ SQLite caching
- ✅ Comprehensive test suite
- ✅ Rich terminal UI
- ✅ Report generation
- ✅ Slack notifications

## MCP Integration Path

The codebase is designed for easy MCP integration. To enable:

1. Implement `MCPJiraClient` subclass in `jira_client.py`
2. Override methods to use `mcp.call_tool()`
3. Update `config.py` to accept MCP server configuration
4. No changes needed to pipeline, rubric, or other modules

Example:
```python
class MCPJiraClient(JiraClient):
    def search_issues(self, jql, fields=None, **kwargs):
        return mcp.call_tool("jira", "search_issues", {
            "jql": jql,
            "fields": fields or self._default_fields()
        })
```

## Next Steps

1. **Configure Environment**
   - Copy `.env.example` to `.env`
   - Fill in Jira credentials
   - Add OpenAI API key
   - Customize JQL query

2. **Test Setup**
   - Run `./setup_check.sh`
   - Run `python -m src.app --dry-run --limit 3`
   - Verify output looks correct

3. **First Production Run**
   - Start with small limit: `--limit 5`
   - Review generated feedback
   - Adjust rubric weights if needed

4. **Automate**
   - Set up cron job or GitHub Actions
   - Configure Slack notifications
   - Monitor reports directory

## Troubleshooting

### "ModuleNotFoundError: No module named 'src'"
Run from project root: `python -m src.app`, not `python src/app.py`

### "No issues found"
Check your JQL query in Jira UI first to verify it returns results

### "Authentication failed"
Verify credentials with:
```bash
curl -u "email:token" https://yourcompany.atlassian.net/rest/api/3/myself
```

### Tests failing
```bash
pip install -e ".[dev]"
pytest -v
```

## Documentation

- **[README.md](README.md)** - User guide and reference
- **[CLAUDE.md](CLAUDE.md)** - Developer guide for AI assistants
- **[.env.example](.env.example)** - Configuration template
- **Module docstrings** - Inline code documentation

## Support

- **Issues**: Report bugs or request features via GitHub Issues
- **Questions**: Check README.md and CLAUDE.md first
- **Tests**: Run `pytest -v` to verify installation

---

**Migration completed successfully! 🎉**

The project is now a modern, production-ready Python CLI tool with DSPy integration.
