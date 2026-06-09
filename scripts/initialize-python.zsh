#!/usr/bin/env zsh
# This script initializes the Python virtual environment and installs project dependencies.

set -e

# Navigate to the project root directory
SCRIPT_DIR="${0:a:h}"
PROJECT_ROOT="${SCRIPT_DIR}/.."
cd "$PROJECT_ROOT"

echo "Initializing Python environment..."

# 1. Create venv if it doesn't exist
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
  echo "No virtual environment found. Creating 'venv'..."
  python3 -m venv venv
  VENV_DIR="venv"
else
  if [ -d "venv" ]; then
    VENV_DIR="venv"
  else
    VENV_DIR=".venv"
  fi
  echo "Virtual environment already exists in '${VENV_DIR}'."
fi

# 2. Activate the virtual environment
echo "Activating virtual environment..."
source "${VENV_DIR}/bin/activate"

# 3. Upgrade pip, setuptools, and wheel
echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# 4. Install dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
  echo "Installing dependencies from requirements.txt..."
  pip install -r requirements.txt
else
  echo "Warning: requirements.txt not found in ${PROJECT_ROOT}."
fi

echo "--------------------------------------------------------"
echo "Python environment initialization complete!"
echo "To activate the environment in your shell, run:"
echo "  source ${VENV_DIR}/bin/activate"
echo ""
echo "To run the automated tests, execute:"
echo "  ./scripts/run_tests.zsh"
echo "--------------------------------------------------------"
