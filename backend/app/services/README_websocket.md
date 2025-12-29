# WebSocket Streaming Documentation

## Overview

The WebSocket streaming functionality provides real-time updates for commodity ETF data. Clients can connect to WebSocket endpoints to receive live updates for prices, signals, flows, and sentiment data.

## Architecture

### Components

1. **WebSocketManager** (`/app/services/websocket_manager.py`)
   - Manages WebSocket connections
   - Handles subscriptions by ticker
   - Broadcasts messages to clients

2. **WebSocket API** (`/app/api/websocket.py`)
   - FastAPI WebSocket endpoints
   - Three main endpoints for different use cases

## Endpoints

### 1. Price Updates: `/api/v1/ws/prices/{ticker}`

Real-time price updates for a specific ticker.

**Parameters:**
- `ticker` (path): ETF ticker symbol (e.g., AGQ, UGL)
- `client_id` (query, optional): Client identifier

**Example:**
```
ws://localhost:8000/api/v1/ws/prices/AGQ
ws://localhost:8000/api/v1/ws/prices/AGQ?client_id=my_client_123
```

**Messages Received:**
```json
{
  "type": "PRICE_UPDATE",
  "ticker": "AGQ",
  "data": {
    "ticker": "AGQ",
    "date": "2025-12-28T12:00:00Z",
    "open": 45.20,
    "high": 45.80,
    "low": 45.10,
    "close": 45.50,
    "volume": 1234567
  },
  "timestamp": "2025-12-28T12:00:00Z"
}
```

### 2. Signal Alerts: `/api/v1/ws/signals`

Trading signal alerts across all or specific tickers.

**Parameters:**
- `client_id` (query, optional): Client identifier
- `tickers` (query, optional): Comma-separated list of tickers

**Example:**
```
ws://localhost:8000/api/v1/ws/signals
ws://localhost:8000/api/v1/ws/signals?tickers=AGQ,UGL
```

**Messages Received:**
```json
{
  "type": "SIGNAL_ALERT",
  "ticker": "AGQ",
  "data": {
    "signal": "BUY",
    "strength": "STRONG",
    "reason": "Flow surge detected",
    "indicators": {...}
  },
  "timestamp": "2025-12-28T12:00:00Z"
}
```

### 3. Dashboard Updates: `/api/v1/ws/dashboard`

Combined updates for dashboard (all message types).

**Parameters:**
- `client_id` (query, optional): Client identifier
- `tickers` (query, optional): Comma-separated list of tickers

**Example:**
```
ws://localhost:8000/api/v1/ws/dashboard
ws://localhost:8000/api/v1/ws/dashboard?tickers=AGQ,UGL,ZSL
```

**Messages Received:**
- PRICE_UPDATE
- SIGNAL_ALERT
- FLOW_UPDATE
- SENTIMENT_UPDATE

### 4. Statistics Endpoint: `/api/v1/ws/stats` (HTTP GET)

Get current WebSocket connection statistics.

**Example:**
```
GET http://localhost:8000/api/v1/ws/stats
```

**Response:**
```json
{
  "status": "success",
  "timestamp": "2025-12-28T12:00:00Z",
  "data": {
    "total_connections": 15,
    "total_subscriptions": 42,
    "tickers_tracked": ["AGQ", "UGL", "ZSL"],
    "ticker_subscriber_counts": {
      "AGQ": 8,
      "UGL": 5,
      "ZSL": 2
    }
  }
}
```

## Message Types

### Client to Server

#### PING
Keep-alive message
```json
{
  "type": "PING"
}
```

Response:
```json
{
  "type": "PONG",
  "timestamp": "2025-12-28T12:00:00Z"
}
```

#### SUBSCRIBE
Subscribe to additional tickers (signals/dashboard endpoints)
```json
{
  "type": "SUBSCRIBE",
  "tickers": ["AGQ", "UGL"]
}
```

#### UNSUBSCRIBE
Unsubscribe from tickers
```json
{
  "type": "UNSUBSCRIBE",
  "tickers": ["ZSL"]
}
```

#### GET_LATEST
Request latest data (price endpoint)
```json
{
  "type": "GET_LATEST"
}
```

#### GET_STATS
Request connection statistics (dashboard endpoint)
```json
{
  "type": "GET_STATS"
}
```

### Server to Client

#### CONNECTION_ESTABLISHED
Sent on successful connection
```json
{
  "type": "CONNECTION_ESTABLISHED",
  "client_id": "price_AGQ_a1b2c3d4",
  "timestamp": "2025-12-28T12:00:00Z"
}
```

#### SUBSCRIPTION_CONFIRMED
Sent after subscribing to tickers
```json
{
  "type": "SUBSCRIPTION_CONFIRMED",
  "tickers": ["AGQ", "UGL"],
  "timestamp": "2025-12-28T12:00:00Z"
}
```

#### PRICE_UPDATE
Real-time price update
```json
{
  "type": "PRICE_UPDATE",
  "ticker": "AGQ",
  "data": {
    "ticker": "AGQ",
    "date": "2025-12-28T12:00:00Z",
    "close": 45.50,
    "volume": 1234567,
    "change_percent": 2.5
  },
  "timestamp": "2025-12-28T12:00:00Z"
}
```

#### SIGNAL_ALERT
Trading signal alert
```json
{
  "type": "SIGNAL_ALERT",
  "ticker": "AGQ",
  "data": {
    "signal": "BUY",
    "strength": "STRONG",
    "confidence": 0.85
  },
  "timestamp": "2025-12-28T12:00:00Z"
}
```

#### FLOW_UPDATE
ETF flow update
```json
{
  "type": "FLOW_UPDATE",
  "ticker": "AGQ",
  "data": {
    "flow_estimate": 15000000,
    "flow_direction": "INFLOW"
  },
  "timestamp": "2025-12-28T12:00:00Z"
}
```

#### SENTIMENT_UPDATE
Sentiment data update
```json
{
  "type": "SENTIMENT_UPDATE",
  "ticker": "AGQ",
  "data": {
    "sentiment_score": 0.75,
    "trending": true
  },
  "timestamp": "2025-12-28T12:00:00Z"
}
```

## Usage Examples

### Python Client

```python
import asyncio
import websockets
import json

async def price_stream():
    uri = "ws://localhost:8000/api/v1/ws/prices/AGQ"

    async with websockets.connect(uri) as websocket:
        # Receive initial messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data['type']} - {data}")

            # Send ping every 30 seconds
            if data['type'] == 'PRICE_UPDATE':
                await websocket.send(json.dumps({"type": "PING"}))

asyncio.run(price_stream())
```

### JavaScript Client

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/prices/AGQ');

ws.onopen = () => {
  console.log('Connected to price stream');

  // Send ping every 30 seconds
  setInterval(() => {
    ws.send(JSON.stringify({ type: 'PING' }));
  }, 30000);
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data.type, data);

  if (data.type === 'PRICE_UPDATE') {
    // Update UI with new price
    updatePriceDisplay(data.data);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from price stream');
};
```

### Dashboard Client (Multiple Tickers)

```javascript
const tickers = ['AGQ', 'UGL', 'ZSL'];
const ws = new WebSocket(
  `ws://localhost:8000/api/v1/ws/dashboard?tickers=${tickers.join(',')}`
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'PRICE_UPDATE':
      updatePrice(data.ticker, data.data);
      break;
    case 'SIGNAL_ALERT':
      showAlert(data.ticker, data.data);
      break;
    case 'FLOW_UPDATE':
      updateFlow(data.ticker, data.data);
      break;
    case 'SENTIMENT_UPDATE':
      updateSentiment(data.ticker, data.data);
      break;
  }
};
```

## Broadcasting Messages from Server

To broadcast updates from your data collection services, use the `websocket_manager`:

```python
from app.services.websocket_manager import websocket_manager

# Broadcast price update to all AGQ subscribers
await websocket_manager.broadcast_to_ticker(
    ticker="AGQ",
    message={
        "type": "PRICE_UPDATE",
        "ticker": "AGQ",
        "data": {
            "close": 45.50,
            "volume": 1234567,
            "change_percent": 2.5
        }
    }
)

# Broadcast signal alert
await websocket_manager.broadcast_to_ticker(
    ticker="AGQ",
    message={
        "type": "SIGNAL_ALERT",
        "ticker": "AGQ",
        "data": {
            "signal": "BUY",
            "strength": "STRONG",
            "confidence": 0.85
        }
    }
)

# Broadcast to all connected clients
await websocket_manager.broadcast_all(
    message={
        "type": "MARKET_STATUS",
        "data": {"status": "CLOSED"}
    }
)
```

## Integration with Data Collectors

Add WebSocket broadcasting to your existing data collectors:

```python
from app.services.websocket_manager import websocket_manager
from app.services.data_storage import data_storage

async def collect_and_broadcast_prices():
    # Collect price data
    prices = await fetch_latest_prices()

    # Save to database
    await data_storage.save_etf_prices(prices)

    # Broadcast to WebSocket clients
    for ticker, price_data in prices.items():
        await websocket_manager.broadcast_to_ticker(
            ticker=ticker,
            message={
                "type": "PRICE_UPDATE",
                "data": price_data
            }
        )
```

## Error Handling

The WebSocket manager automatically handles:
- Disconnected clients (removes from subscription lists)
- Failed message sends (logs and disconnects client)
- Invalid JSON (logs warning)

Clients should implement:
- Reconnection logic on disconnect
- Message validation
- Timeout handling for responses

## Performance Considerations

- Connections are lightweight and stateful
- Messages are sent asynchronously
- Failed sends don't block other clients
- Automatic cleanup of disconnected clients
- No message queueing (real-time only)

## Security Notes

- Add authentication if needed (JWT tokens in query params)
- Validate client permissions for ticker access
- Rate limit message sends if needed
- Consider adding CORS for WebSocket connections
- Monitor connection counts and bandwidth

## Testing

Test WebSocket endpoints using tools like:
- `websocat`: `websocat ws://localhost:8000/api/v1/ws/prices/AGQ`
- Postman (WebSocket support)
- Browser Developer Tools
- Python `websockets` library
- JavaScript `WebSocket` API
