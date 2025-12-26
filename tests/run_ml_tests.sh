#!/bin/bash
"""
Test Suite Runner for Health Insurance ML Pipeline
Executes all ML-specific and pipeline tests with coverage reporting
"""

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
LOGS_DIR="$PROJECT_ROOT/logs/tests"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Health Insurance ML Pipeline Test Suite Runner            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Test categories
TEST_SUITES=(
    "test_ml_models.py:ML Models & Performance"
    "test_data_pipeline.py:Data Quality & Pipeline"
    "test_feature_engineering.py:Feature Engineering"
)

TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0

# Run each test suite
for suite_info in "${TEST_SUITES[@]}"; do
    IFS=':' read -r test_file suite_name <<< "$suite_info"
    
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Running: $suite_name${NC}"
    echo -e "${YELLOW}File: $test_file${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    test_path="$TESTS_DIR/unit/$test_file"
    log_file="$LOGS_DIR/${test_file%.py}_results.txt"
    
    if [ ! -f "$test_path" ]; then
        echo -e "${RED}✗ Test file not found: $test_path${NC}"
        ((TOTAL_FAILED++))
        continue
    fi
    
    # Run pytest with coverage
    if python -m pytest "$test_path" \
        --tb=short \
        -v \
        --color=yes \
        --junit-xml="$LOGS_DIR/${test_file%.py}_junit.xml" \
        2>&1 | tee "$log_file"; then
        echo -e "${GREEN}✓ $suite_name PASSED${NC}"
        ((TOTAL_PASSED++))
    else
        echo -e "${RED}✗ $suite_name FAILED${NC}"
        ((TOTAL_FAILED++))
    fi
    
    echo ""
done

# Generate coverage report
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Generating Coverage Report${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if python -m pytest "$TESTS_DIR/unit" \
    --cov=config \
    --cov=src \
    --cov=scripts \
    --cov-report=term-missing \
    --cov-report=html:"$LOGS_DIR/coverage_html" \
    --cov-report=json:"$LOGS_DIR/coverage.json" \
    -v --tb=short 2>&1 | tee "$LOGS_DIR/coverage_report.txt"; then
    echo -e "${GREEN}✓ Coverage report generated${NC}"
else
    echo -e "${YELLOW}⚠ Coverage report generation had issues${NC}"
fi

echo ""

# Summary
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                       TEST SUMMARY                             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All test suites passed!${NC}"
    SUMMARY_COLOR=$GREEN
    SUMMARY_ICON="✓"
else
    echo -e "${RED}✗ Some test suites failed${NC}"
    SUMMARY_COLOR=$RED
    SUMMARY_ICON="✗"
fi

echo ""
echo -e "${SUMMARY_COLOR}Suites Passed:   $TOTAL_PASSED${NC}"
echo -e "${SUMMARY_COLOR}Suites Failed:   $TOTAL_FAILED${NC}"
echo ""
echo "Test Results:"
echo "  └─ JUnit XML: $LOGS_DIR/*_junit.xml"
echo "  └─ Coverage:  $LOGS_DIR/coverage_html/index.html"
echo "  └─ Reports:   $LOGS_DIR/"
echo ""

# Create summary JSON
summary_json="$LOGS_DIR/test_summary.json"
cat > "$summary_json" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "total_suites": ${#TEST_SUITES[@]},
  "passed": $TOTAL_PASSED,
  "failed": $TOTAL_FAILED,
  "status": "$([ $TOTAL_FAILED -eq 0 ] && echo 'PASS' || echo 'FAIL')"
}
EOF

echo "Summary saved to: $summary_json"
echo ""

if [ $TOTAL_FAILED -eq 0 ]; then
    exit 0
else
    exit 1
fi
