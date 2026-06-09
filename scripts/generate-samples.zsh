#!/usr/bin/env zsh
# This script wraps the Python sample data generator, ensuring the virtual environment is activated.

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
  echo "Warning: No virtual environment (venv or .venv) found. Running with global python..."
fi

# Run the python script and pass along any arguments (like --count)
python scripts/generate_sample_data.py "$@"
