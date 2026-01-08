#!/bin/bash
# Setup verification script for DSPy Jira Feedback

set -e

echo "🔍 DSPy Jira Feedback - Setup Verification"
echo "=========================================="
echo ""

# Check Python version
echo "✓ Checking Python version..."
python --version || { echo "❌ Python not found. Please install Python 3.11+"; exit 1; }

PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$PYTHON_VERSION < 3.11" | bc -l) )); then
    echo "❌ Python 3.11+ required, found $PYTHON_VERSION"
    exit 1
fi
echo "   Python $PYTHON_VERSION ✓"
echo ""

# Check virtual environment
echo "✓ Checking virtual environment..."
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "   Virtual environment active: $VIRTUAL_ENV ✓"
else
    echo "⚠️  No virtual environment detected. Recommended to use venv:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
fi
echo ""

# Check .env file
echo "✓ Checking configuration..."
if [ -f ".env" ]; then
    echo "   .env file found ✓"

    # Check required variables
    if grep -q "JIRA_BASE_URL=" .env; then
        echo "   - JIRA_BASE_URL configured ✓"
    else
        echo "   ⚠️  JIRA_BASE_URL not set in .env"
    fi

    if grep -q "JIRA_API_TOKEN=" .env; then
        echo "   - JIRA_API_TOKEN configured ✓"
    else
        echo "   ⚠️  JIRA_API_TOKEN not set in .env"
    fi

    if grep -q "OPENAI_API_KEY=" .env; then
        echo "   - OPENAI_API_KEY configured ✓"
    else
        echo "   ⚠️  OPENAI_API_KEY not set in .env"
    fi
else
    echo "   ⚠️  .env file not found. Copy from .env.example:"
    echo "   cp .env.example .env"
fi
echo ""

# Check project structure
echo "✓ Checking project structure..."
if [ -d "src" ] && [ -d "tests" ]; then
    echo "   Project directories found ✓"
    echo "   - src/ ($(ls -1 src/*.py 2>/dev/null | wc -l | tr -d ' ') modules)"
    echo "   - tests/ ($(ls -1 tests/test_*.py 2>/dev/null | wc -l | tr -d ' ') test files)"
else
    echo "   ❌ Project structure incomplete"
    exit 1
fi
echo ""

# Try importing dependencies
echo "✓ Checking dependencies..."
python -c "import dspy" 2>/dev/null && echo "   - dspy ✓" || echo "   ⚠️  dspy not installed"
python -c "import pydantic" 2>/dev/null && echo "   - pydantic ✓" || echo "   ⚠️  pydantic not installed"
python -c "import dotenv" 2>/dev/null && echo "   - python-dotenv ✓" || echo "   ⚠️  python-dotenv not installed"
python -c "import rich" 2>/dev/null && echo "   - rich ✓" || echo "   ⚠️  rich not installed"
python -c "import httpx" 2>/dev/null && echo "   - httpx ✓" || echo "   ⚠️  httpx not installed"

MISSING_DEPS=$(python -c "
import sys
try:
    import dspy, pydantic, dotenv, rich, httpx
    sys.exit(0)
except ImportError:
    sys.exit(1)
" 2>/dev/null && echo "0" || echo "1")

if [ "$MISSING_DEPS" = "1" ]; then
    echo ""
    echo "   ⚠️  Some dependencies missing. Install with:"
    echo "   pip install -e ."
fi
echo ""

# Summary
echo "=========================================="
echo "Setup Status:"
if [ "$MISSING_DEPS" = "0" ] && [ -f ".env" ]; then
    echo "✅ Ready to run!"
    echo ""
    echo "Try these commands:"
    echo "  python -m src.app --dry-run --limit 5"
    echo "  python -m src.app --stats"
    echo "  pytest"
else
    echo "⚠️  Setup incomplete. Follow the steps above."
fi
echo ""
