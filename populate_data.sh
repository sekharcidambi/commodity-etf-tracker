#!/bin/bash

# Data Population Script for Commodity ETF Tracker
# This script populates all necessary data for the dashboard

echo "🚀 Starting data population for Commodity ETF Tracker..."
echo ""

API_URL="http://localhost:8000"

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to make API call and display result
call_api() {
    local endpoint=$1
    local description=$2

    echo -e "${BLUE}[INFO]${NC} $description"
    response=$(curl -s -X POST "$API_URL$endpoint" -w "\n%{http_code}")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        echo -e "${GREEN}[SUCCESS]${NC} HTTP $http_code - $endpoint"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        echo -e "${RED}[ERROR]${NC} HTTP $http_code - $endpoint"
        echo "$body"
    fi
    echo ""
    sleep 2
}

echo "================================================"
echo "STEP 1: Collecting Price Data (1 year history)"
echo "================================================"
echo ""

# Collect price data for AGQ and UGL (1 year)
call_api "/api/v1/data/collect/etf/AGQ?period=1y" "Collecting AGQ price data (1 year)"
call_api "/api/v1/data/collect/etf/UGL?period=1y" "Collecting UGL price data (1 year)"

echo "================================================"
echo "STEP 2: Collecting ETF Flow Data"
echo "================================================"
echo ""

# Collect flow data from ETFdb
call_api "/api/v1/flows/collect/etfdb" "Collecting flow data from ETFdb.com"

echo "================================================"
echo "STEP 3: Collecting Institutional Holdings (13F)"
echo "================================================"
echo ""

# Collect institutional holdings for AGQ and UGL
call_api "/api/v1/flows/collect/institutional/AGQ" "Collecting 13F holdings for AGQ"
call_api "/api/v1/flows/collect/institutional/UGL" "Collecting 13F holdings for UGL"

echo "================================================"
echo "STEP 4: Generating Trading Signals"
echo "================================================"
echo ""

echo -e "${BLUE}[INFO]${NC} Trading signals are generated automatically based on flow and price data"
echo -e "${BLUE}[INFO]${NC} Signals will appear in the dashboard once patterns are detected"
echo ""

echo "================================================"
echo "✅ Data Population Complete!"
echo "================================================"
echo ""
echo "Summary:"
echo "- ✅ Price data collected for AGQ and UGL (1 year)"
echo "- ✅ Flow data collected from ETFdb.com"
echo "- ✅ Institutional holdings collected (13F filings)"
echo "- ⏳ Trading signals will generate based on collected data"
echo ""
echo "📊 Visit http://localhost:5173 to view the dashboard"
echo ""
echo "Note: Some features may show 'No data available' if:"
echo "  - Investor segment data (investor_segment_flows table) is not populated"
echo "  - No trading signals match current conditions"
echo ""
echo "To manually trigger signal generation, use:"
echo "  curl -X POST http://localhost:8000/api/v1/signals/generate/AGQ"
echo "  curl -X POST http://localhost:8000/api/v1/signals/generate/UGL"
echo ""
