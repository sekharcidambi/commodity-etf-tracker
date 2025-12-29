"""
WebSocket Integration Examples

Shows how to integrate WebSocket broadcasting into existing data collection services.
"""

from datetime import datetime
from typing import List, Dict, Any
from loguru import logger

# Import the WebSocket manager
from app.services.websocket_manager import websocket_manager
from app.services.data_storage import data_storage


# Example 1: Broadcast price updates after collecting data
async def collect_and_broadcast_prices(tickers: List[str]):
    """
    Collect price data and broadcast to WebSocket clients

    This would be integrated into your existing price collection service
    """
    logger.info(f"Collecting prices for {len(tickers)} tickers with WebSocket broadcast")

    for ticker in tickers:
        try:
            # Fetch latest price from database
            prices = await data_storage.get_price_data(ticker=ticker, limit=1)

            if prices:
                price_data = prices[0]

                # Broadcast to all subscribers of this ticker
                sent_count = await websocket_manager.broadcast_to_ticker(
                    ticker=ticker,
                    message={
                        "type": "PRICE_UPDATE",
                        "ticker": ticker,
                        "data": price_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                logger.debug(f"Broadcasted price update for {ticker} to {sent_count} clients")

        except Exception as e:
            logger.error(f"Error broadcasting price for {ticker}: {e}")


# Example 2: Broadcast signal alerts when generated
async def generate_and_broadcast_signal(ticker: str, signal_data: Dict[str, Any]):
    """
    Generate trading signal and broadcast to WebSocket clients

    This would be integrated into your signal generation service
    """
    try:
        # Broadcast signal alert
        sent_count = await websocket_manager.broadcast_to_ticker(
            ticker=ticker,
            message={
                "type": "SIGNAL_ALERT",
                "ticker": ticker,
                "data": signal_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        logger.info(
            f"Signal alert for {ticker}: {signal_data.get('signal')} "
            f"(sent to {sent_count} clients)"
        )

    except Exception as e:
        logger.error(f"Error broadcasting signal for {ticker}: {e}")


# Example 3: Broadcast flow updates
async def broadcast_flow_update(ticker: str, flow_data: Dict[str, Any]):
    """
    Broadcast flow data updates

    This would be integrated into your flow collection service
    """
    try:
        sent_count = await websocket_manager.broadcast_to_ticker(
            ticker=ticker,
            message={
                "type": "FLOW_UPDATE",
                "ticker": ticker,
                "data": flow_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        logger.debug(f"Broadcasted flow update for {ticker} to {sent_count} clients")

    except Exception as e:
        logger.error(f"Error broadcasting flow for {ticker}: {e}")


# Example 4: Broadcast sentiment updates
async def broadcast_sentiment_update(ticker: str, sentiment_data: Dict[str, Any]):
    """
    Broadcast sentiment data updates

    This would be integrated into your sentiment collection service
    """
    try:
        sent_count = await websocket_manager.broadcast_to_ticker(
            ticker=ticker,
            message={
                "type": "SENTIMENT_UPDATE",
                "ticker": ticker,
                "data": sentiment_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        logger.debug(f"Broadcasted sentiment update for {ticker} to {sent_count} clients")

    except Exception as e:
        logger.error(f"Error broadcasting sentiment for {ticker}: {e}")


# Example 5: Broadcast global market status
async def broadcast_market_status(status: str, message: str):
    """
    Broadcast global market status to all connected clients

    Example: Market open/close, system maintenance, etc.
    """
    try:
        sent_count = await websocket_manager.broadcast_all(
            message={
                "type": "MARKET_STATUS",
                "data": {
                    "status": status,
                    "message": message
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"Broadcasted market status to {sent_count} clients: {status} - {message}")

    except Exception as e:
        logger.error(f"Error broadcasting market status: {e}")


# Example 6: Integration with scheduler
async def scheduled_data_collection_with_broadcast():
    """
    Example of scheduled task that collects data and broadcasts updates

    This would be called by APScheduler or similar
    """
    from app.services.data_collector import data_collector

    logger.info("Starting scheduled data collection with WebSocket broadcast")

    try:
        # Collect data (existing functionality)
        stats = await data_collector.collect_daily_prices(period="1d")

        # Broadcast that data collection completed
        await websocket_manager.broadcast_all(
            message={
                "type": "DATA_COLLECTION_COMPLETE",
                "data": {
                    "tickers_processed": stats['tickers_processed'],
                    "records_saved": stats['records_saved']
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        logger.success(
            f"Data collection complete and broadcasted to "
            f"{websocket_manager.get_connection_stats()['total_connections']} clients"
        )

    except Exception as e:
        logger.error(f"Error in scheduled data collection: {e}")


# Example 7: Enhanced signal generator with WebSocket
class SignalGeneratorWithWebSocket:
    """
    Example of enhancing existing SignalGenerator to broadcast signals
    """

    def __init__(self):
        # Import existing signal generator
        from app.services.signal_generator import SignalGeneratorService
        self.signal_generator = SignalGeneratorService()

    async def generate_signals_with_broadcast(self, ticker: str):
        """
        Generate signals and broadcast to WebSocket clients
        """
        try:
            # Generate signals using existing service
            signals = await self.signal_generator.generate_signals(ticker)

            # If signals were generated, broadcast them
            if signals:
                for signal in signals:
                    await websocket_manager.broadcast_to_ticker(
                        ticker=ticker,
                        message={
                            "type": "SIGNAL_ALERT",
                            "ticker": ticker,
                            "data": {
                                "signal": signal.get("signal_type"),
                                "strength": signal.get("strength"),
                                "confidence": signal.get("confidence"),
                                "indicators": signal.get("indicators"),
                                "reason": signal.get("description")
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )

                logger.info(f"Generated and broadcasted {len(signals)} signals for {ticker}")

        except Exception as e:
            logger.error(f"Error generating signals with broadcast for {ticker}: {e}")


# Example 8: Wrapper function for API endpoints
async def update_price_with_broadcast(ticker: str, price_data: Dict[str, Any]):
    """
    Wrapper function that can be used in API endpoints to update and broadcast

    Usage in API:
        from examples.websocket_integration_example import update_price_with_broadcast

        @router.post("/prices/update/{ticker}")
        async def update_price(ticker: str, price_data: PriceUpdate):
            await update_price_with_broadcast(ticker, price_data.dict())
            return {"status": "success"}
    """
    try:
        # Save to database
        # await data_storage.save_price(ticker, price_data)

        # Broadcast to WebSocket clients
        await websocket_manager.broadcast_to_ticker(
            ticker=ticker,
            message={
                "type": "PRICE_UPDATE",
                "ticker": ticker,
                "data": price_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"Price updated and broadcasted for {ticker}")

    except Exception as e:
        logger.error(f"Error updating price for {ticker}: {e}")
        raise


# Example 9: Monitoring WebSocket connections
async def log_websocket_stats():
    """
    Log current WebSocket connection statistics

    Could be called periodically or on-demand
    """
    stats = websocket_manager.get_connection_stats()

    logger.info("=" * 60)
    logger.info("WebSocket Connection Statistics")
    logger.info("=" * 60)
    logger.info(f"Total Connections: {stats['total_connections']}")
    logger.info(f"Total Subscriptions: {stats['total_subscriptions']}")
    logger.info(f"Tickers Tracked: {', '.join(stats['tickers_tracked']) or 'None'}")

    if stats['ticker_subscriber_counts']:
        logger.info("\nSubscriber counts by ticker:")
        for ticker, count in stats['ticker_subscriber_counts'].items():
            logger.info(f"  {ticker}: {count} subscribers")

    logger.info("=" * 60)


# Example 10: Custom message broadcasting
async def broadcast_custom_alert(
    ticker: str,
    alert_type: str,
    message: str,
    severity: str = "INFO"
):
    """
    Broadcast custom alerts to clients

    Args:
        ticker: Ticker symbol
        alert_type: Type of alert (e.g., "VOLUME_SPIKE", "PRICE_ANOMALY")
        message: Alert message
        severity: Alert severity (INFO, WARNING, CRITICAL)
    """
    try:
        sent_count = await websocket_manager.broadcast_to_ticker(
            ticker=ticker,
            message={
                "type": "CUSTOM_ALERT",
                "ticker": ticker,
                "data": {
                    "alert_type": alert_type,
                    "message": message,
                    "severity": severity
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        logger.warning(
            f"[{severity}] Alert for {ticker}: {alert_type} - {message} "
            f"(sent to {sent_count} clients)"
        )

    except Exception as e:
        logger.error(f"Error broadcasting custom alert: {e}")


# Example usage in your existing services:
"""
# In your data_collector.py or similar:

from app.services.websocket_manager import websocket_manager

class DataCollector:
    async def collect_daily_prices(self, tickers=None, period="5d"):
        # ... existing collection code ...

        for ticker in tickers:
            # Fetch data
            df = self.yf_collector.fetch_etf_data(ticker, period=period)

            if not df.empty:
                # Save to database
                saved = await self.storage.save_etf_prices(df)

                # NEW: Broadcast to WebSocket clients
                if saved > 0:
                    latest_price = df.iloc[-1].to_dict()
                    await websocket_manager.broadcast_to_ticker(
                        ticker=ticker,
                        message={
                            "type": "PRICE_UPDATE",
                            "ticker": ticker,
                            "data": latest_price
                        }
                    )

        return stats
"""
