# Backend Scripts

## Data Collection Test

Test the yfinance data collector and database storage:

```bash
# From the backend directory
cd /home/user/commodity-etf-tracker/backend

# Make sure database is running
docker-compose up -d postgres

# Run the test script
python scripts/test_collection.py
```

This script will:
1. Collect 5 days of price data for AGQ and UGL
2. Collect 5 days of futures data for gold (GC=F) and silver (SI=F)
3. Save all data to the database
4. Retrieve and display sample data to verify it was saved

## Using the API

Once the backend is running with `docker-compose up`:

```bash
# Trigger daily data collection for all tickers
curl -X POST "http://localhost:8000/api/v1/data/collect/daily?period=5d"

# Collect data for a single ticker
curl -X POST "http://localhost:8000/api/v1/data/collect/etf/AGQ?period=1mo"

# Backfill historical data
curl -X POST "http://localhost:8000/api/v1/data/backfill?ticker=AGQ&start_date=2024-01-01&end_date=2024-12-31"

# Get collected price data
curl "http://localhost:8000/api/v1/prices/etf/AGQ?limit=10"
```

## API Documentation

View full API documentation at:
- http://localhost:8000/api/docs (Swagger UI)
- http://localhost:8000/api/redoc (ReDoc)
