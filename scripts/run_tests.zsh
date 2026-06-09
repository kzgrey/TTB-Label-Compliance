#!/usr/bin/env zsh
# This script automates running the unit tests and generating a code coverage report.

set -e

# Navigate to the project root directory
SCRIPT_DIR="${0:a:h}"
PROJECT_ROOT="${SCRIPT_DIR}/.."
cd "$PROJECT_ROOT"

# Check if a virtual environment is present and activate it
if [ -d "venv" ]; then
  echo "Activating virtual environment: venv"
  source venv/bin/activate
elif [ -d ".venv" ]; then
  echo "Activating virtual environment: .venv"
  source .venv/bin/activate
else
  echo "Warning: No virtual environment (venv or .venv) found. Running with global python/pytest..."
fi

# Ensure pytest and pytest-cov are installed
if ! command -v pytest &> /dev/null; then
  echo "Error: pytest is not installed or not in the PATH."
  echo "Please run 'pip install -r requirements.txt' to install the necessary testing tools."
  exit 1
fi

# Run pytest with coverage reporting
echo "Running tests with code coverage..."
# We pass "$@" to allow users to specify specific test files or flags,
# e.g., ./scripts/run_tests.zsh tests/test_backend.py -v
# --cov=src: Measure coverage of the src/ directory
# --cov-report=term: Show coverage summary in the terminal
# --cov-report=html: Generate HTML coverage report in htmlcov/
pytest --cov=src --cov-report=term --cov-report=html "$@"

echo "--------------------------------------------------------"
echo "Tests and code coverage run complete!"
echo "HTML coverage report generated: file://${PROJECT_ROOT}/htmlcov/index.html"
echo "--------------------------------------------------------"
