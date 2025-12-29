"""WebSocket endpoints for real-time data streaming"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
from datetime import datetime
from loguru import logger
import uuid
import json

from app.services.websocket_manager import websocket_manager
from app.services.data_storage import data_storage

router = APIRouter()


@router.websocket("/ws/prices/{ticker}")
async def websocket_price_updates(
    websocket: WebSocket,
    ticker: str,
    client_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time price updates for a specific ticker

    Args:
        ticker: ETF ticker symbol (e.g., AGQ, UGL, ZSL)
        client_id: Optional client identifier (generated if not provided)

    Message types sent:
    - PRICE_UPDATE: Real-time price changes
    - CONNECTION_ESTABLISHED: Connection confirmation
    - SUBSCRIPTION_CONFIRMED: Subscription confirmation
    """
    # Generate client_id if not provided
    if not client_id:
        client_id = f"price_{ticker}_{uuid.uuid4().hex[:8]}"

    ticker = ticker.upper()

    try:
        # Connect client
        await websocket_manager.connect(websocket, client_id)

        # Auto-subscribe to the ticker
        await websocket_manager.subscribe(client_id, [ticker])

        # Send initial price data
        try:
            latest_prices = await data_storage.get_price_data(
                ticker=ticker,
                limit=1
            )
            if latest_prices:
                await websocket_manager.send_personal(
                    client_id,
                    {
                        "type": "PRICE_UPDATE",
                        "ticker": ticker,
                        "data": latest_prices[0],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        except Exception as e:
            logger.warning(f"Could not fetch initial price data for {ticker}: {e}")

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (e.g., ping, requests)
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle different message types from client
                msg_type = message.get("type")

                if msg_type == "PING":
                    await websocket_manager.send_personal(
                        client_id,
                        {"type": "PONG", "timestamp": datetime.utcnow().isoformat()}
                    )
                elif msg_type == "GET_LATEST":
                    # Client requesting latest price
                    try:
                        latest = await data_storage.get_price_data(ticker=ticker, limit=1)
                        if latest:
                            await websocket_manager.send_personal(
                                client_id,
                                {
                                    "type": "PRICE_UPDATE",
                                    "ticker": ticker,
                                    "data": latest[0],
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                    except Exception as e:
                        logger.error(f"Error fetching latest price for {ticker}: {e}")

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {e}")

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected from price stream for {ticker}")
    except Exception as e:
        logger.error(f"Error in price WebSocket for {ticker}: {e}")
    finally:
        websocket_manager.disconnect(client_id)


@router.websocket("/ws/signals")
async def websocket_signal_alerts(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None),
    tickers: Optional[str] = Query(None, description="Comma-separated list of tickers")
):
    """
    WebSocket endpoint for trading signal alerts

    Args:
        client_id: Optional client identifier (generated if not provided)
        tickers: Optional comma-separated ticker list to filter signals

    Message types sent:
    - SIGNAL_ALERT: New trading signals
    - CONNECTION_ESTABLISHED: Connection confirmation
    """
    # Generate client_id if not provided
    if not client_id:
        client_id = f"signals_{uuid.uuid4().hex[:8]}"

    try:
        # Connect client
        await websocket_manager.connect(websocket, client_id)

        # Subscribe to specific tickers if provided
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",")]
            await websocket_manager.subscribe(client_id, ticker_list)
            logger.info(f"Client {client_id} subscribed to signals for: {ticker_list}")
        else:
            logger.info(f"Client {client_id} connected to all signals")

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                msg_type = message.get("type")

                if msg_type == "PING":
                    await websocket_manager.send_personal(
                        client_id,
                        {"type": "PONG", "timestamp": datetime.utcnow().isoformat()}
                    )
                elif msg_type == "SUBSCRIBE":
                    # Client requesting to subscribe to additional tickers
                    new_tickers = message.get("tickers", [])
                    if new_tickers:
                        await websocket_manager.subscribe(client_id, new_tickers)
                elif msg_type == "UNSUBSCRIBE":
                    # Client requesting to unsubscribe from tickers
                    remove_tickers = message.get("tickers", [])
                    if remove_tickers:
                        await websocket_manager.unsubscribe(client_id, remove_tickers)

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {e}")

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected from signal alerts")
    except Exception as e:
        logger.error(f"Error in signals WebSocket: {e}")
    finally:
        websocket_manager.disconnect(client_id)


@router.websocket("/ws/dashboard")
async def websocket_dashboard(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None),
    tickers: Optional[str] = Query(None, description="Comma-separated list of tickers")
):
    """
    WebSocket endpoint for combined dashboard updates

    Streams all types of updates:
    - PRICE_UPDATE: Real-time price changes
    - SIGNAL_ALERT: New trading signals
    - FLOW_UPDATE: Flow data updates
    - SENTIMENT_UPDATE: Sentiment changes

    Args:
        client_id: Optional client identifier (generated if not provided)
        tickers: Optional comma-separated ticker list to filter updates
    """
    # Generate client_id if not provided
    if not client_id:
        client_id = f"dashboard_{uuid.uuid4().hex[:8]}"

    try:
        # Connect client
        await websocket_manager.connect(websocket, client_id)

        # Subscribe to tickers if provided
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",")]
            await websocket_manager.subscribe(client_id, ticker_list)
            logger.info(f"Dashboard client {client_id} subscribed to: {ticker_list}")

            # Send initial data for subscribed tickers
            for ticker in ticker_list:
                try:
                    # Get latest price
                    prices = await data_storage.get_price_data(ticker=ticker, limit=1)
                    if prices:
                        await websocket_manager.send_personal(
                            client_id,
                            {
                                "type": "PRICE_UPDATE",
                                "ticker": ticker,
                                "data": prices[0],
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )

                    # Get latest flow data
                    flows = await data_storage.get_flow_data(ticker=ticker, limit=1)
                    if flows:
                        await websocket_manager.send_personal(
                            client_id,
                            {
                                "type": "FLOW_UPDATE",
                                "ticker": ticker,
                                "data": flows[0],
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )
                except Exception as e:
                    logger.warning(f"Error fetching initial data for {ticker}: {e}")
        else:
            logger.info(f"Dashboard client {client_id} connected (all tickers)")

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                msg_type = message.get("type")

                if msg_type == "PING":
                    await websocket_manager.send_personal(
                        client_id,
                        {"type": "PONG", "timestamp": datetime.utcnow().isoformat()}
                    )
                elif msg_type == "SUBSCRIBE":
                    # Client requesting to subscribe to additional tickers
                    new_tickers = message.get("tickers", [])
                    if new_tickers:
                        await websocket_manager.subscribe(client_id, new_tickers)
                elif msg_type == "UNSUBSCRIBE":
                    # Client requesting to unsubscribe from tickers
                    remove_tickers = message.get("tickers", [])
                    if remove_tickers:
                        await websocket_manager.unsubscribe(client_id, remove_tickers)
                elif msg_type == "GET_STATS":
                    # Client requesting connection statistics
                    stats = websocket_manager.get_connection_stats()
                    await websocket_manager.send_personal(
                        client_id,
                        {
                            "type": "STATS",
                            "data": stats,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {e}")

    except WebSocketDisconnect:
        logger.info(f"Dashboard client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Error in dashboard WebSocket: {e}")
    finally:
        websocket_manager.disconnect(client_id)


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics

    Returns information about active connections, subscriptions, and tickers
    """
    stats = websocket_manager.get_connection_stats()
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": stats
    }
