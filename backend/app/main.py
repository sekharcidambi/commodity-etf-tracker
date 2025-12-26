"""Main FastAPI application"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.api import api_router

# Configure logger
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

app = FastAPI(
    title="Commodity ETF Tracker API",
    description="Real-time commodity ETF flow tracking and signal generation",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Commodity ETF Tracker API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/api/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "commodity-etf-tracker",
            "version": "0.1.0"
        }
    )


@app.on_event("startup")
async def startup_event():
    """Execute on application startup"""
    logger.info("🚀 Starting Commodity ETF Tracker API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL}")


@app.on_event("shutdown")
async def shutdown_event():
    """Execute on application shutdown"""
    logger.info("👋 Shutting down Commodity ETF Tracker API...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
