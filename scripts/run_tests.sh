#!/bin/bash
set -e  # Exit immediately on failure

echo "🚀 Running unit tests with coverage..."
poetry run pytest tests/unit --cov=src --cov-report=term --cov-append

echo "🧪 Running integration tests with coverage..."
poetry run pytest tests/integration -m integration --cov=src --cov-report=term --cov-append

echo "📊 Combining coverage data and generating final report..."
poetry run coverage combine
poetry run coverage report --fail-under=75
