# Quick Start Guide

Get the Commodity ETF Tracker running locally in minutes!

## Prerequisites

- Docker and Docker Compose installed
- Git
- (Optional) Node.js 20+ and Python 3.11+ for local development without Docker

## Step 1: Clone and Setup

```bash
cd /home/user/commodity-etf-tracker

# Copy environment template
cp .env.example .env

# Edit .env and add your API keys (optional for MVP)
# nano .env
```

## Step 2: Start Services

```bash
# Start all services (PostgreSQL, Redis, Backend, Frontend)
docker compose up -d

# Check logs
docker compose logs -f
```

Services will be available at:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Step 3: Initialize Database

The database will be automatically initialized with TimescaleDB schema when PostgreSQL starts.

Check database:
```bash
docker compose exec postgres psql -U postgres -d commodity_tracker -c "\dt"
```

You should see tables like:
- commodity_prices
- etf_prices
- etf_flows
- investor_segment_flows
- tickers
- signals
- etc.

## Step 4: Test the API

```bash
# Health check
curl http://localhost:8000/health

# Get tickers list
curl http://localhost:8000/api/v1/tickers/

# API documentation
open http://localhost:8000/api/docs
```

## Step 5: Start Building!

The project structure is ready. Next steps:

### Backend Development

```bash
cd backend

# Install dependencies locally (optional, for IDE support)
pip install -r requirements.txt

# Run tests
pytest

# The backend auto-reloads on code changes when running via Docker Compose
```

### Frontend Development

```bash
cd frontend

# Install dependencies locally (optional, for IDE support)
npm install

# The frontend auto-reloads on code changes when running via Docker Compose
```

## API Keys Setup (Optional for MVP)

To enable real data collection, get free API keys from:

1. **Twelve Data** (800 calls/day free): https://twelvedata.com/
2. **FRED** (unlimited free): https://fred.stlouisfed.org/docs/api/api_key.html
3. **Alpha Vantage** (25 calls/day free): https://www.alphavantage.co/

Add them to `.env`:
```env
TWELVE_DATA_API_KEY=your_key_here
FRED_API_KEY=your_key_here
ALPHA_VANTAGE_API_KEY=your_key_here
DATA_COLLECTION_ENABLED=true
```

Restart services:
```bash
docker compose restart backend
```

## Stopping Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (clears database)
docker compose down -v
```

## Troubleshooting

### Database connection issues
```bash
# Check if PostgreSQL is running
docker compose ps postgres

# View PostgreSQL logs
docker compose logs postgres

# Restart PostgreSQL
docker compose restart postgres
```

### Backend not starting
```bash
# View backend logs
docker compose logs backend

# Rebuild backend
docker compose build backend
docker compose up -d backend
```

### Frontend not loading
```bash
# View frontend logs
docker compose logs frontend

# Rebuild frontend
docker compose build frontend
docker compose up -d frontend
```

## Development Workflow

1. **Make changes** to code (auto-reloads in Docker)
2. **Test locally** using the API docs at http://localhost:8000/api/docs
3. **Commit changes** to Git
4. **Push** to your repository

## Next Steps

- Implement data collectors in `backend/app/services/`
- Create React components in `frontend/src/components/`
- Add database queries in `backend/app/db/`
- Build analytics in `backend/app/services/analytics.py`
- Add charts to frontend using Recharts

See [REQUIREMENTS.md](./REQUIREMENTS.md) for full system specifications.

## Project Structure

```
commodity-etf-tracker/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Configuration
│   │   ├── db/           # Database connection
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # Business logic
│   │   └── utils/        # Helpers
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API clients
│   │   └── hooks/        # Custom hooks
│   ├── package.json
│   └── Dockerfile
├── database/
│   └── sql/              # Database initialization
├── docker-compose.yml
├── .env.example
└── README.md
```

## Support

- Check [REQUIREMENTS.md](./REQUIREMENTS.md) for detailed specifications
- See [Issues](https://github.com/yourusername/commodity-etf-tracker/issues) for known issues
- Read API docs at http://localhost:8000/api/docs when running
