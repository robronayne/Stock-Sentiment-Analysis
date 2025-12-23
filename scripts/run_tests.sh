#!/bin/bash

# Test runner script for Stock Sentiment Analysis Bot

set -e

echo "================================================"
echo "Stock Sentiment Analysis Bot - Test Suite"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if test dependencies are installed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}Test dependencies not found. Installing...${NC}"
    pip install -r requirements-test.txt
    echo ""
fi

# Parse arguments
TEST_TYPE="${1:-all}"
COVERAGE="${2:-no-coverage}"

case "$TEST_TYPE" in
    "all")
        echo "Running all tests..."
        if [ "$COVERAGE" = "coverage" ]; then
            pytest --cov=app --cov-report=term-missing --cov-report=html -v
        else
            pytest -v
        fi
        ;;
    "unit")
        echo "Running unit tests only..."
        pytest -m unit -v
        ;;
    "integration")
        echo "Running integration tests only..."
        pytest -m integration -v
        ;;
    "fast")
        echo "Running fast tests (excluding slow)..."
        pytest -m "not slow" -v
        ;;
    "dedup")
        echo "Running deduplication tests..."
        pytest tests/unit/test_deduplicator.py -v
        ;;
    "validator")
        echo "Running validator tests..."
        pytest tests/unit/test_validator.py -v
        ;;
    "llm")
        echo "Running LLM service tests..."
        pytest tests/unit/test_llm_service.py -v
        ;;
    "workflow")
        echo "Running workflow tests..."
        pytest tests/integration/ -v
        ;;
    "scenarios")
        echo "Running scenario tests..."
        pytest tests/integration/test_recommendation_scenarios.py -v
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./run_tests.sh [type] [coverage]"
        echo ""
        echo "Test types:"
        echo "  all          - Run all tests (default)"
        echo "  unit         - Unit tests only"
        echo "  integration  - Integration tests only"
        echo "  fast         - Fast tests only (exclude slow)"
        echo "  dedup        - Deduplication tests"
        echo "  validator    - Validator tests"
        echo "  llm          - LLM service tests"
        echo "  workflow     - Workflow integration tests"
        echo "  scenarios    - Recommendation scenario tests"
        echo ""
        echo "Coverage:"
        echo "  coverage     - Generate coverage report"
        echo "  no-coverage  - Skip coverage (default)"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh all coverage"
        echo "  ./run_tests.sh unit"
        echo "  ./run_tests.sh integration"
        exit 1
        ;;
esac

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}================================================${NC}"
    
    if [ "$COVERAGE" = "coverage" ]; then
        echo ""
        echo "Coverage report generated:"
        echo "  • Terminal: See above"
        echo "  • HTML: open htmlcov/index.html"
    fi
else
    echo -e "${RED}================================================${NC}"
    echo -e "${RED}✗ Tests failed${NC}"
    echo -e "${RED}================================================${NC}"
fi

echo ""
exit $EXIT_CODE
