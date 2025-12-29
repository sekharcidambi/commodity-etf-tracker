# WebSocket Examples

This directory contains examples and documentation for using the WebSocket streaming functionality in the Commodity ETF Tracker.

## Files

### Documentation
- **README_websocket_examples.md** (this file) - Overview and usage guide

### Example Clients
- **websocket_client_example.py** - Python WebSocket client
- **websocket_client.html** - Interactive HTML/JavaScript WebSocket client
- **websocket_integration_example.py** - Integration examples for server-side broadcasting

### Configuration
- **requirements.txt** - Python dependencies for running the examples

## Quick Start

### 1. Start the FastAPI Server

Make sure your backend server is running:

```bash
cd /home/user/commodity-etf-tracker/backend
python -m uvicorn app.main:app --reload
```

The server should be running at `http://localhost:8000`

### 2. Test with HTML Client (Easiest)

Simply open `websocket_client.html` in your web browser:

```bash
# On Linux
xdg-open examples/websocket_client.html

# On macOS
open examples/websocket_client.html

# On Windows
start examples/websocket_client.html
```

Or just drag the file into your browser.

**Usage:**
1. Select an endpoint (Prices, Signals, or Dashboard)
2. Enter ticker(s) if needed
3. Click "Connect"
4. Watch real-time updates appear!

### 3. Test with Python Client

Install dependencies:

```bash
cd /home/user/commodity-etf-tracker/backend/examples
pip install -r requirements.txt
```

Run the Python client:

```bash
# Price updates for AGQ
python websocket_client_example.py --endpoint prices --ticker AGQ

# Signal alerts for multiple tickers
python websocket_client_example.py --endpoint signals --tickers AGQ,UGL,ZSL

# Dashboard updates (all message types)
python websocket_client_example.py --endpoint dashboard --tickers AGQ,UGL
```

Press `Ctrl+C` to disconnect.

### 4. Test with Command Line (websocat)

Install websocat:
```bash
# On macOS
brew install websocat

# On Linux
cargo install websocat
# or download from https://github.com/vi/websocat/releases
```

Connect to WebSocket:
```bash
# Price updates for AGQ
websocat ws://localhost:8000/api/v1/ws/prices/AGQ

# Signal alerts
websocat ws://localhost:8000/api/v1/ws/signals

# Dashboard with specific tickers
websocat "ws://localhost:8000/api/v1/ws/dashboard?tickers=AGQ,UGL"
```

## WebSocket Endpoints

### Price Updates: `/api/v1/ws/prices/{ticker}`

Real-time price updates for a specific ticker.

**Example:**
```
ws://localhost:8000/api/v1/ws/prices/AGQ
```

**Receives:**
- PRICE_UPDATE messages for the specified ticker
- CONNECTION_ESTABLISHED on connect
- PONG in response to PING

**Send:**
- `{"type": "PING"}` - Keep connection alive
- `{"type": "GET_LATEST"}` - Request latest price

### Signal Alerts: `/api/v1/ws/signals`

Trading signal alerts.

**Example:**
```
ws://localhost:8000/api/v1/ws/signals?tickers=AGQ,UGL
```

**Receives:**
- SIGNAL_ALERT messages
- CONNECTION_ESTABLISHED on connect
- SUBSCRIPTION_CONFIRMED after subscribing

**Send:**
- `{"type": "PING"}` - Keep connection alive
- `{"type": "SUBSCRIBE", "tickers": ["ZSL"]}` - Subscribe to additional tickers
- `{"type": "UNSUBSCRIBE", "tickers": ["AGQ"]}` - Unsubscribe from tickers

### Dashboard: `/api/v1/ws/dashboard`

Combined updates for dashboard.

**Example:**
```
ws://localhost:8000/api/v1/ws/dashboard?tickers=AGQ,UGL,ZSL
```

**Receives:**
- PRICE_UPDATE
- SIGNAL_ALERT
- FLOW_UPDATE
- SENTIMENT_UPDATE
- All other message types

**Send:**
- `{"type": "PING"}` - Keep connection alive
- `{"type": "SUBSCRIBE", "tickers": ["PPLT"]}` - Subscribe to additional tickers
- `{"type": "UNSUBSCRIBE", "tickers": ["AGQ"]}` - Unsubscribe from tickers
- `{"type": "GET_STATS"}` - Get connection statistics

## Message Types

### Client → Server

```json
// Keep connection alive
{"type": "PING"}

// Subscribe to tickers (signals/dashboard only)
{"type": "SUBSCRIBE", "tickers": ["AGQ", "UGL"]}

// Unsubscribe from tickers
{"type": "UNSUBSCRIBE", "tickers": ["ZSL"]}

// Request latest data (prices endpoint)
{"type": "GET_LATEST"}

// Request stats (dashboard endpoint)
{"type": "GET_STATS"}
```

### Server → Client

```json
// Connection established
{
  "type": "CONNECTION_ESTABLISHED",
  "client_id": "price_AGQ_a1b2c3d4",
  "timestamp": "2025-12-28T12:00:00Z"
}

// Price update
{
  "type": "PRICE_UPDATE",
  "ticker": "AGQ",
  "data": {
    "close": 45.50,
    "volume": 1234567,
    "change_percent": 2.5
  },
  "timestamp": "2025-12-28T12:00:00Z"
}

// Signal alert
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

// Flow update
{
  "type": "FLOW_UPDATE",
  "ticker": "AGQ",
  "data": {
    "flow_estimate": 15000000,
    "flow_direction": "INFLOW"
  },
  "timestamp": "2025-12-28T12:00:00Z"
}

// Sentiment update
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

## Integration with Your Services

See `websocket_integration_example.py` for detailed examples of how to integrate WebSocket broadcasting into your existing services.

### Quick Example

```python
from app.services.websocket_manager import websocket_manager

# Broadcast price update
await websocket_manager.broadcast_to_ticker(
    ticker="AGQ",
    message={
        "type": "PRICE_UPDATE",
        "ticker": "AGQ",
        "data": {"close": 45.50, "volume": 1234567}
    }
)

# Broadcast to all clients
await websocket_manager.broadcast_all(
    message={
        "type": "MARKET_STATUS",
        "data": {"status": "OPEN"}
    }
)
```

## Testing

### 1. Manual Testing with HTML Client

1. Open `websocket_client.html` in browser
2. Connect to price endpoint for AGQ
3. In another terminal, trigger a price update (if you have that functionality)
4. Watch the update appear in the HTML client

### 2. Testing Broadcasting

Create a simple test script:

```python
import asyncio
from app.services.websocket_manager import websocket_manager

async def test_broadcast():
    # Give clients time to connect
    await asyncio.sleep(5)

    # Broadcast test message
    await websocket_manager.broadcast_to_ticker(
        ticker="AGQ",
        message={
            "type": "PRICE_UPDATE",
            "ticker": "AGQ",
            "data": {"close": 45.50, "volume": 1234567}
        }
    )

asyncio.run(test_broadcast())
```

### 3. Load Testing

For production, consider load testing with tools like:
- **artillery** - WebSocket load testing
- **k6** - General load testing with WebSocket support
- **locust** - Python-based load testing

## Monitoring

### Get Connection Statistics

HTTP endpoint:
```bash
curl http://localhost:8000/api/v1/ws/stats
```

Response:
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

### From Python Code

```python
from app.services.websocket_manager import websocket_manager

stats = websocket_manager.get_connection_stats()
print(f"Total connections: {stats['total_connections']}")
print(f"Tickers tracked: {stats['tickers_tracked']}")
```

## Troubleshooting

### Connection Refused

**Problem:** Can't connect to WebSocket
```
Error: Connection refused
```

**Solution:**
1. Make sure the backend server is running
2. Check the URL (should be `ws://localhost:8000` not `http://`)
3. Check firewall settings

### No Messages Received

**Problem:** Connected but not receiving any messages

**Solution:**
1. Check that you're subscribed to the right tickers
2. Verify data is being collected and saved to the database
3. Add broadcasting calls to your data collection services (see integration examples)
4. Check server logs for errors

### Connection Drops

**Problem:** Connection drops after a few minutes

**Solution:**
1. Implement ping/pong keep-alive (examples do this automatically)
2. Check network stability
3. Implement reconnection logic in your client

### Invalid JSON

**Problem:** Getting JSON decode errors

**Solution:**
1. Ensure all messages are valid JSON
2. Check that you're sending strings, not objects
3. Use `JSON.stringify()` in JavaScript or `json.dumps()` in Python

## Production Considerations

### Security

1. **Authentication:** Add JWT token validation
   ```python
   @router.websocket("/ws/prices/{ticker}")
   async def websocket_price_updates(
       websocket: WebSocket,
       ticker: str,
       token: str = Query(...)
   ):
       # Validate token
       user = await verify_token(token)
       if not user:
           await websocket.close(code=1008)  # Policy violation
           return
       # ... rest of code
   ```

2. **Rate Limiting:** Limit connections per user/IP
3. **Input Validation:** Validate all incoming messages
4. **CORS:** Configure CORS for WebSocket connections

### Performance

1. **Message Batching:** Batch updates if sending frequently
2. **Compression:** Enable WebSocket compression
3. **Connection Limits:** Set max connections per user
4. **Horizontal Scaling:** Use Redis Pub/Sub for multi-server setups

### Reliability

1. **Reconnection Logic:** Implement in clients
2. **Message Persistence:** Queue important messages
3. **Health Checks:** Monitor WebSocket endpoint health
4. **Logging:** Log connection events and errors

## Next Steps

1. Integrate broadcasting into your data collection services
2. Add authentication to WebSocket endpoints
3. Implement reconnection logic in frontend
4. Add monitoring and alerting for WebSocket metrics
5. Consider Redis Pub/Sub for scaling across multiple servers

## Resources

- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket Protocol Specification](https://tools.ietf.org/html/rfc6455)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Python websockets Library](https://websockets.readthedocs.io/)

## Support

For issues or questions:
1. Check the logs in `logs/app.log`
2. Review the main WebSocket documentation in `/backend/app/services/README_websocket.md`
3. Look at integration examples in `websocket_integration_example.py`
