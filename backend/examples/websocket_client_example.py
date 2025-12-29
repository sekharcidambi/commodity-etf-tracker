"""
WebSocket Client Example

Demonstrates how to connect to the commodity ETF tracker WebSocket endpoints
and receive real-time updates.

Usage:
    python websocket_client_example.py --endpoint prices --ticker AGQ
    python websocket_client_example.py --endpoint signals --tickers AGQ,UGL
    python websocket_client_example.py --endpoint dashboard
"""

import asyncio
import websockets
import json
import argparse
from datetime import datetime


class WebSocketClient:
    """Example WebSocket client for commodity ETF tracker"""

    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url

    async def connect_price_stream(self, ticker: str):
        """Connect to price update stream for a specific ticker"""
        uri = f"{self.base_url}/api/v1/ws/prices/{ticker}"
        print(f"Connecting to price stream: {uri}")

        try:
            async with websockets.connect(uri) as websocket:
                print(f"✓ Connected to {ticker} price stream")

                # Set up ping interval
                ping_task = asyncio.create_task(self._ping_loop(websocket))

                try:
                    async for message in websocket:
                        await self._handle_message(message)
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed by server")
                finally:
                    ping_task.cancel()

        except Exception as e:
            print(f"✗ Connection error: {e}")

    async def connect_signal_stream(self, tickers: list = None):
        """Connect to signal alert stream"""
        uri = f"{self.base_url}/api/v1/ws/signals"
        if tickers:
            uri += f"?tickers={','.join(tickers)}"

        print(f"Connecting to signal stream: {uri}")

        try:
            async with websockets.connect(uri) as websocket:
                print("✓ Connected to signal stream")

                # Set up ping interval
                ping_task = asyncio.create_task(self._ping_loop(websocket))

                try:
                    async for message in websocket:
                        await self._handle_message(message)
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed by server")
                finally:
                    ping_task.cancel()

        except Exception as e:
            print(f"✗ Connection error: {e}")

    async def connect_dashboard(self, tickers: list = None):
        """Connect to dashboard stream"""
        uri = f"{self.base_url}/api/v1/ws/dashboard"
        if tickers:
            uri += f"?tickers={','.join(tickers)}"

        print(f"Connecting to dashboard stream: {uri}")

        try:
            async with websockets.connect(uri) as websocket:
                print("✓ Connected to dashboard stream")

                # Set up ping interval
                ping_task = asyncio.create_task(self._ping_loop(websocket))

                try:
                    async for message in websocket:
                        await self._handle_message(message)
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed by server")
                finally:
                    ping_task.cancel()

        except Exception as e:
            print(f"✗ Connection error: {e}")

    async def _ping_loop(self, websocket, interval: int = 30):
        """Send periodic ping messages to keep connection alive"""
        try:
            while True:
                await asyncio.sleep(interval)
                await websocket.send(json.dumps({"type": "PING"}))
                print("[→] Sent PING")
        except asyncio.CancelledError:
            pass

    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            timestamp = datetime.fromisoformat(
                data.get("timestamp", datetime.utcnow().isoformat()).replace("Z", "+00:00")
            )

            # Format output based on message type
            if msg_type == "CONNECTION_ESTABLISHED":
                print(f"\n[✓] Connection established")
                print(f"    Client ID: {data.get('client_id')}")

            elif msg_type == "SUBSCRIPTION_CONFIRMED":
                print(f"\n[✓] Subscription confirmed")
                print(f"    Tickers: {', '.join(data.get('tickers', []))}")

            elif msg_type == "PONG":
                print(f"[←] Received PONG")

            elif msg_type == "PRICE_UPDATE":
                ticker = data.get("ticker")
                price_data = data.get("data", {})
                print(f"\n[💰] PRICE UPDATE - {ticker}")
                print(f"    Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                if "close" in price_data:
                    print(f"    Close: ${price_data['close']:.2f}")
                if "volume" in price_data:
                    print(f"    Volume: {price_data['volume']:,}")
                if "change_percent" in price_data:
                    change = price_data['change_percent']
                    arrow = "📈" if change > 0 else "📉"
                    print(f"    Change: {arrow} {change:+.2f}%")

            elif msg_type == "SIGNAL_ALERT":
                ticker = data.get("ticker")
                signal_data = data.get("data", {})
                print(f"\n[🚨] SIGNAL ALERT - {ticker}")
                print(f"    Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                if "signal" in signal_data:
                    signal = signal_data['signal']
                    emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"
                    print(f"    Signal: {emoji} {signal}")
                if "strength" in signal_data:
                    print(f"    Strength: {signal_data['strength']}")
                if "confidence" in signal_data:
                    print(f"    Confidence: {signal_data['confidence']:.1%}")

            elif msg_type == "FLOW_UPDATE":
                ticker = data.get("ticker")
                flow_data = data.get("data", {})
                print(f"\n[💸] FLOW UPDATE - {ticker}")
                print(f"    Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                if "flow_estimate" in flow_data:
                    flow = flow_data['flow_estimate']
                    print(f"    Flow: ${flow:,.0f}")
                if "flow_direction" in flow_data:
                    direction = flow_data['flow_direction']
                    arrow = "⬆️" if direction == "INFLOW" else "⬇️"
                    print(f"    Direction: {arrow} {direction}")

            elif msg_type == "SENTIMENT_UPDATE":
                ticker = data.get("ticker")
                sentiment_data = data.get("data", {})
                print(f"\n[😊] SENTIMENT UPDATE - {ticker}")
                print(f"    Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                if "sentiment_score" in sentiment_data:
                    score = sentiment_data['sentiment_score']
                    emoji = "😄" if score > 0.6 else "😐" if score > 0.4 else "😞"
                    print(f"    Score: {emoji} {score:.2f}")
                if "trending" in sentiment_data:
                    trending = "🔥 TRENDING" if sentiment_data['trending'] else "Normal"
                    print(f"    Status: {trending}")

            elif msg_type == "STATS":
                stats_data = data.get("data", {})
                print(f"\n[📊] CONNECTION STATS")
                print(f"    Total Connections: {stats_data.get('total_connections', 0)}")
                print(f"    Total Subscriptions: {stats_data.get('total_subscriptions', 0)}")
                print(f"    Tickers Tracked: {', '.join(stats_data.get('tickers_tracked', []))}")

            else:
                print(f"\n[?] {msg_type}")
                print(f"    {json.dumps(data, indent=2)}")

        except json.JSONDecodeError as e:
            print(f"✗ Error decoding message: {e}")
        except Exception as e:
            print(f"✗ Error handling message: {e}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="WebSocket Client Example")
    parser.add_argument(
        "--endpoint",
        choices=["prices", "signals", "dashboard"],
        required=True,
        help="WebSocket endpoint to connect to"
    )
    parser.add_argument(
        "--ticker",
        help="Ticker symbol (for price endpoint)"
    )
    parser.add_argument(
        "--tickers",
        help="Comma-separated tickers (for signals/dashboard endpoints)"
    )
    parser.add_argument(
        "--url",
        default="ws://localhost:8000",
        help="Base WebSocket URL (default: ws://localhost:8000)"
    )

    args = parser.parse_args()

    client = WebSocketClient(base_url=args.url)

    try:
        if args.endpoint == "prices":
            if not args.ticker:
                print("Error: --ticker required for price endpoint")
                return
            await client.connect_price_stream(args.ticker.upper())

        elif args.endpoint == "signals":
            tickers = None
            if args.tickers:
                tickers = [t.strip().upper() for t in args.tickers.split(",")]
            await client.connect_signal_stream(tickers)

        elif args.endpoint == "dashboard":
            tickers = None
            if args.tickers:
                tickers = [t.strip().upper() for t in args.tickers.split(",")]
            await client.connect_dashboard(tickers)

    except KeyboardInterrupt:
        print("\n\nDisconnecting...")


if __name__ == "__main__":
    print("=" * 60)
    print("Commodity ETF Tracker - WebSocket Client Example")
    print("=" * 60)
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
