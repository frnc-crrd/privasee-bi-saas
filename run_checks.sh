#!/bin/bash
# ----------------------------------------------------
# Automated Quality Gate Script
# This script runs Ruff (Linter/Formatter) and Pytest.
# ----------------------------------------------------

echo "--- 1. Running Ruff Linter and Formatter ---"

# 1. Run the Linter and fix any simple issues
ruff check . --fix
if [ $? -ne 0 ]; then
    echo "Ruff check failed (non-fixable errors detected). Please review."
    exit 1
fi

# 2. Run the Formatter to enforce style
ruff format .
if [ $? -ne 0 ]; then
    echo "Ruff formatting failed."
    exit 1
fi

echo "Ruff checks completed successfully (code is clean and formatted)."

echo ""
echo "--- 2. Running Pytest (Test Suite) ---"

# 3. Run the Tests
pytest
if [ $? -ne 0 ]; then
    echo "Pytest failed! One or more tests are broken."
    exit 1
fi

echo "All tests passed successfully!"
echo ""
echo "Quality Gate Passed. Ready to commit."

# Exit successfully
exit 0
