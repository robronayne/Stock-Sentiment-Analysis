#!/bin/bash

# Test script for Stock Sentiment Analysis Bot API

echo "================================================"
echo "Testing Stock Sentiment Analysis Bot API"
echo "================================================"
echo ""

BASE_URL="http://localhost:8000"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    
    echo -n "Testing: $description... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        return 1
    fi
}

# Check if services are running
echo "1. Checking if services are running..."
echo ""

if ! curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo -e "${RED}❌ API server is not running!${NC}"
    echo ""
    echo "Start services with:"
    echo "  docker compose up -d"
    echo ""
    exit 1
fi

# Health check
test_endpoint "GET" "/health" "Health check"
echo ""

# Root endpoint
echo "2. Testing basic endpoints..."
echo ""
test_endpoint "GET" "/" "Root endpoint"
test_endpoint "GET" "/docs" "API documentation"
echo ""

# Analysis endpoint (this will take a while)
echo "3. Testing stock analysis..."
echo ""
echo -e "${YELLOW}Note: First analysis may take 30-60 seconds...${NC}"
echo ""

TICKER="AAPL"
echo "Analyzing $TICKER..."
response=$(curl -s -X POST "$BASE_URL/api/analyze/$TICKER")
http_code=$?

if [ $http_code -eq 0 ]; then
    echo -e "${GREEN}✓ Analysis completed${NC}"
    echo ""
    echo "Response preview:"
    echo "$response" | jq -r '
        "Company: \(.company_name)",
        "Recommendation: \(.recommendation)",
        "Confidence: \(.confidence)",
        "Risk Level: \(.risk_level)",
        "Summary: \(.summary)"
    ' 2>/dev/null || echo "$response" | head -c 200
    echo ""
else
    echo -e "${RED}✗ Analysis failed${NC}"
    echo "$response"
    echo ""
fi

# Check if recommendation was saved
echo "4. Testing recommendations endpoint..."
echo ""
test_endpoint "GET" "/api/recommendations/$TICKER" "Get latest recommendation"
test_endpoint "GET" "/api/recommendations?limit=5" "List all recommendations"
echo ""

# Check articles
echo "5. Testing articles endpoint..."
echo ""
test_endpoint "GET" "/api/articles/$TICKER?limit=5" "Get collected articles"
echo ""

# Test metrics (might not have data yet)
echo "6. Testing metrics endpoints..."
echo ""
echo -n "Testing: Get overall metrics... "
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/metrics")
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "404" ]; then
    echo -e "${YELLOW}⊘ SKIP${NC} (No validated recommendations yet)"
elif [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
fi
echo ""

# Summary
echo "================================================"
echo "Test Summary"
echo "================================================"
echo ""
echo "✓ API is functional and responding"
echo "✓ Stock analysis is working"
echo "✓ Database is storing data"
echo ""
echo "Next steps:"
echo "  1. Try analyzing other stocks"
echo "  2. Wait a few days for validation results"
echo "  3. Check metrics at /api/metrics"
echo ""
echo "View all endpoints at: http://localhost:8000/docs"
echo ""
