"""WebSocket connection manager for real-time updates"""

from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket
from loguru import logger
import json


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting

    Handles:
    - Connection lifecycle (connect/disconnect)
    - Ticker subscriptions
    - Message broadcasting (per-ticker, global, personal)
    - Different message types (PRICE_UPDATE, SIGNAL_ALERT, FLOW_UPDATE, SENTIMENT_UPDATE)
    """

    def __init__(self):
        # Active connections: client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

        # Ticker subscriptions: ticker -> set of client_ids
        self.ticker_subscriptions: Dict[str, Set[str]] = {}

        # Client to tickers mapping: client_id -> set of tickers
        self.client_tickers: Dict[str, Set[str]] = {}

        logger.info("WebSocket Manager initialized")

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        Accept and register a new WebSocket connection

        Args:
            websocket: The WebSocket connection
            client_id: Unique identifier for the client
        """
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            self.client_tickers[client_id] = set()

            logger.info(
                f"Client {client_id} connected. Total connections: {len(self.active_connections)}"
            )

            # Send welcome message
            await self.send_personal(
                client_id,
                {
                    "type": "CONNECTION_ESTABLISHED",
                    "client_id": client_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error connecting client {client_id}: {e}")
            raise

    def disconnect(self, client_id: str) -> None:
        """
        Remove a WebSocket connection and clean up subscriptions

        Args:
            client_id: Unique identifier for the client
        """
        try:
            # Remove from active connections
            if client_id in self.active_connections:
                del self.active_connections[client_id]

            # Clean up ticker subscriptions
            if client_id in self.client_tickers:
                tickers = self.client_tickers[client_id]
                for ticker in tickers:
                    if ticker in self.ticker_subscriptions:
                        self.ticker_subscriptions[ticker].discard(client_id)
                        # Remove ticker entry if no subscribers left
                        if not self.ticker_subscriptions[ticker]:
                            del self.ticker_subscriptions[ticker]

                del self.client_tickers[client_id]

            logger.info(
                f"Client {client_id} disconnected. "
                f"Remaining connections: {len(self.active_connections)}"
            )

        except Exception as e:
            logger.error(f"Error disconnecting client {client_id}: {e}")

    async def subscribe(self, client_id: str, tickers: List[str]) -> None:
        """
        Subscribe a client to ticker updates

        Args:
            client_id: Unique identifier for the client
            tickers: List of ticker symbols to subscribe to
        """
        try:
            if client_id not in self.active_connections:
                logger.warning(f"Cannot subscribe: client {client_id} not connected")
                return

            for ticker in tickers:
                ticker = ticker.upper()

                # Add to ticker subscriptions
                if ticker not in self.ticker_subscriptions:
                    self.ticker_subscriptions[ticker] = set()
                self.ticker_subscriptions[ticker].add(client_id)

                # Add to client's ticker list
                if client_id not in self.client_tickers:
                    self.client_tickers[client_id] = set()
                self.client_tickers[client_id].add(ticker)

            logger.info(
                f"Client {client_id} subscribed to {len(tickers)} tickers: {tickers}"
            )

            # Send confirmation
            await self.send_personal(
                client_id,
                {
                    "type": "SUBSCRIPTION_CONFIRMED",
                    "tickers": tickers,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error subscribing client {client_id} to {tickers}: {e}")

    async def unsubscribe(self, client_id: str, tickers: List[str]) -> None:
        """
        Unsubscribe a client from ticker updates

        Args:
            client_id: Unique identifier for the client
            tickers: List of ticker symbols to unsubscribe from
        """
        try:
            if client_id not in self.active_connections:
                logger.warning(f"Cannot unsubscribe: client {client_id} not connected")
                return

            for ticker in tickers:
                ticker = ticker.upper()

                # Remove from ticker subscriptions
                if ticker in self.ticker_subscriptions:
                    self.ticker_subscriptions[ticker].discard(client_id)
                    if not self.ticker_subscriptions[ticker]:
                        del self.ticker_subscriptions[ticker]

                # Remove from client's ticker list
                if client_id in self.client_tickers:
                    self.client_tickers[client_id].discard(ticker)

            logger.info(
                f"Client {client_id} unsubscribed from {len(tickers)} tickers: {tickers}"
            )

            # Send confirmation
            await self.send_personal(
                client_id,
                {
                    "type": "UNSUBSCRIPTION_CONFIRMED",
                    "tickers": tickers,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error unsubscribing client {client_id} from {tickers}: {e}")

    async def broadcast_to_ticker(
        self,
        ticker: str,
        message: Dict[str, Any],
        message_type: Optional[str] = None
    ) -> int:
        """
        Broadcast a message to all subscribers of a specific ticker

        Args:
            ticker: Ticker symbol
            message: Message data to broadcast
            message_type: Type of message (PRICE_UPDATE, SIGNAL_ALERT, etc.)

        Returns:
            Number of clients the message was sent to
        """
        ticker = ticker.upper()

        # Ensure message has required fields
        if "type" not in message and message_type:
            message["type"] = message_type
        if "ticker" not in message:
            message["ticker"] = ticker
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        # Get subscribers for this ticker
        subscribers = self.ticker_subscriptions.get(ticker, set())

        if not subscribers:
            logger.debug(f"No subscribers for ticker {ticker}")
            return 0

        # Send to all subscribers
        sent_count = 0
        disconnected_clients = []

        for client_id in subscribers:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error sending to client {client_id}: {e}")
                    disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

        logger.debug(
            f"Broadcast {message.get('type', 'MESSAGE')} for {ticker} "
            f"to {sent_count} subscribers"
        )

        return sent_count

    async def broadcast_all(
        self,
        message: Dict[str, Any],
        message_type: Optional[str] = None
    ) -> int:
        """
        Broadcast a message to all connected clients

        Args:
            message: Message data to broadcast
            message_type: Type of message

        Returns:
            Number of clients the message was sent to
        """
        # Ensure message has required fields
        if "type" not in message and message_type:
            message["type"] = message_type
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        sent_count = 0
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

        logger.debug(
            f"Broadcast {message.get('type', 'MESSAGE')} to {sent_count} clients"
        )

        return sent_count

    async def send_personal(
        self,
        client_id: str,
        message: Dict[str, Any],
        message_type: Optional[str] = None
    ) -> bool:
        """
        Send a message to a specific client

        Args:
            client_id: Unique identifier for the client
            message: Message data to send
            message_type: Type of message

        Returns:
            True if sent successfully, False otherwise
        """
        if client_id not in self.active_connections:
            logger.warning(f"Cannot send to client {client_id}: not connected")
            return False

        # Ensure message has required fields
        if "type" not in message and message_type:
            message["type"] = message_type
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        try:
            websocket = self.active_connections[client_id]
            await websocket.send_json(message)
            logger.debug(f"Sent {message.get('type', 'MESSAGE')} to client {client_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            self.disconnect(client_id)
            return False

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active connections and subscriptions

        Returns:
            Dictionary with connection statistics
        """
        return {
            "total_connections": len(self.active_connections),
            "total_subscriptions": sum(
                len(clients) for clients in self.ticker_subscriptions.values()
            ),
            "tickers_tracked": list(self.ticker_subscriptions.keys()),
            "ticker_subscriber_counts": {
                ticker: len(clients)
                for ticker, clients in self.ticker_subscriptions.items()
            }
        }

    def get_client_subscriptions(self, client_id: str) -> List[str]:
        """
        Get list of tickers a client is subscribed to

        Args:
            client_id: Unique identifier for the client

        Returns:
            List of ticker symbols
        """
        return list(self.client_tickers.get(client_id, set()))


# Singleton instance
websocket_manager = WebSocketManager()
