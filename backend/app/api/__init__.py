"""API router aggregation"""

from fastapi import APIRouter

from app.api import prices, flows, signals, analytics, tickers

api_router = APIRouter()

api_router.include_router(
    prices.router,
    prefix="/prices",
    tags=["Prices"]
)

api_router.include_router(
    flows.router,
    prefix="/flows",
    tags=["ETF Flows"]
)

api_router.include_router(
    signals.router,
    prefix="/signals",
    tags=["Trading Signals"]
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"]
)

api_router.include_router(
    tickers.router,
    prefix="/tickers",
    tags=["Tickers"]
)
