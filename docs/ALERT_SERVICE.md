# Alert Service Documentation

The Alert Service provides a comprehensive alert delivery system for the Commodity ETF Tracker, supporting multiple delivery channels and alert types.

## Overview

The alert service enables real-time notifications for trading signals and market events through multiple channels:

- **IN_APP**: Store alerts in database for frontend display
- **EMAIL**: Send alerts via SMTP
- **SLACK**: Send alerts via Slack webhook
- **WEBHOOK**: Generic webhook for custom integrations

## Features

### 1. Multiple Delivery Channels

Supports four delivery channels that can be used independently or in combination:

```python
from app.services.alert_service import alert_service, AlertChannel

await alert_service.send_alert(
    alert_type="SIGNAL_GENERATED",
    ticker="AGQ",
    message="Buy signal detected",
    channels=[AlertChannel.IN_APP, AlertChannel.EMAIL],
    recipient="trader@example.com"
)
```

### 2. Alert Types

The service supports six predefined alert types:

- `SIGNAL_GENERATED`: New trading signal created
- `EXTREME_FLOW`: Extreme flow detected (z-score > 2.0)
- `COT_EXTREME`: COT at extreme positioning
- `SQUEEZE_WARNING`: COMEX inventory squeeze detected
- `SENTIMENT_SPIKE`: Unusual retail activity
- `PRICE_ALERT`: Price threshold crossed

### 3. Alert Deduplication

Automatic deduplication prevents alert spam:

- **Signal alerts**: 1 hour cooldown (configurable via `ALERT_COOLDOWN_MINUTES`)
- **Extreme conditions**: 24 hour cooldown (configurable via `ALERT_EXTREME_COOLDOWN_MINUTES`)

The same alert type for the same ticker won't be sent again within the cooldown period.

### 4. Alert History & Tracking

All alerts are logged in the `alert_log` table with:

- Alert type, ticker, channel, recipient
- Message content
- Status (PENDING, SENT, FAILED)
- Sent timestamp
- Error message (if failed)

## Configuration

Add these settings to your `.env` file:

```bash
# SMTP Configuration (for email alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=alerts@commodity-tracker.com
SMTP_FROM_NAME=Commodity ETF Tracker

# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Alert Cooldown Settings
ALERT_COOLDOWN_MINUTES=60
ALERT_EXTREME_COOLDOWN_MINUTES=1440
```

## Usage Examples

### Send a Signal Alert

```python
from app.services.alert_service import alert_service, AlertChannel

# Create signal data (typically from SignalGeneratorService)
signal_data = {
    "ticker": "AGQ",
    "signal_type": "EXTREME_FLOW",
    "direction": "BUY",
    "strength": 0.85,
    "trigger_values": {
        "z_score": 2.45,
        "percentile": 98.2,
        "rolling_sum_4w": 125.3
    },
    "notes": "Extreme inflow detected",
    "expires_at": datetime.now() + timedelta(days=14)
}

# Send via multiple channels
result = await alert_service.create_signal_alert(
    signal_data=signal_data,
    channels=[AlertChannel.IN_APP, AlertChannel.EMAIL],
    recipient="trader@example.com"
)
```

### Send a Custom Alert

```python
result = await alert_service.send_alert(
    alert_type=AlertType.PRICE_ALERT,
    ticker="UGL",
    message="UGL has crossed $50 price threshold",
    data={
        "current_price": 50.15,
        "threshold": 50.00,
        "change_pct": 2.3
    },
    channels=[AlertChannel.IN_APP, AlertChannel.SLACK]
)
```

### Get Alert History

```python
# Get all alerts for a ticker
alerts = await alert_service.get_alert_history(
    ticker="AGQ",
    limit=50
)

# Get pending alerts
pending = await alert_service.get_pending_alerts()

# Get alerts by type
signal_alerts = await alert_service.get_alert_history(
    alert_type=AlertType.SIGNAL_GENERATED,
    limit=20
)

# Get alerts by channel
email_alerts = await alert_service.get_alert_history(
    channel=AlertChannel.EMAIL,
    status="SENT",
    limit=100
)
```

### Subscribe a User

```python
# Note: This is a simplified implementation
# In production, store subscriptions in a database table
subscription = await alert_service.subscribe_user(
    user_id="user_123",
    alert_types=[
        AlertType.SIGNAL_GENERATED,
        AlertType.EXTREME_FLOW,
        AlertType.COT_EXTREME
    ],
    channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
    recipient="trader@example.com"
)
```

### Mark Alert as Delivered

```python
success = await alert_service.mark_alert_delivered(
    alert_id=123,
    status="SENT"
)
```

## Integration with Signal Generator

The alert service integrates seamlessly with the SignalGeneratorService:

```python
from app.services.signal_generator import SignalGeneratorService
from app.services.alert_service import alert_service, AlertChannel

# Generate signals
signal_gen = SignalGeneratorService()
signals = await signal_gen.generate_signals("AGQ")

# Send alerts for each signal
for signal in signals:
    await alert_service.create_signal_alert(
        signal_data=signal,
        channels=[AlertChannel.IN_APP, AlertChannel.EMAIL],
        recipient="trader@example.com"
    )
```

## Email Format

Emails are sent in both plain text and HTML formats:

**Subject**: `[Commodity ETF Tracker] {alert_type}: {ticker}`

**Body** includes:
- Alert type and ticker
- Timestamp
- Message content
- Key metrics (from trigger values)
- Professional formatting with HTML styling

## Slack Format

Slack messages use the Blocks API with:

- Color-coded attachments (green for BUY, red for SELL, orange for WATCH)
- Structured fields for alert type and ticker
- Message content
- Timestamp footer

## Webhook Format

Generic webhooks receive a JSON payload:

```json
{
  "alert_type": "SIGNAL_GENERATED",
  "ticker": "AGQ",
  "message": "Buy signal detected...",
  "data": {
    "signal_type": "EXTREME_FLOW",
    "direction": "BUY",
    "strength": 0.85,
    "trigger_values": {...}
  },
  "timestamp": "2025-12-28T10:30:00"
}
```

## Database Schema

The `alert_log` table structure:

```sql
CREATE TABLE IF NOT EXISTS alert_log (
    id SERIAL PRIMARY KEY,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    alert_type VARCHAR(50) NOT NULL,
    ticker VARCHAR(10),
    channel VARCHAR(20) NOT NULL,
    recipient VARCHAR(200),
    message TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Error Handling

The service includes comprehensive error handling:

- Failed email sends are logged with error messages
- Slack webhook failures are caught and logged
- All errors are stored in the `alert_log` table
- Failed alerts can be retried or investigated later

## Future Enhancements

Planned improvements:

1. **User Subscription Table**: Store user preferences in database
2. **Alert Templates**: Customizable message templates
3. **Retry Logic**: Automatic retry for failed deliveries
4. **Rate Limiting**: Per-user rate limits
5. **Batch Alerts**: Digest emails for multiple alerts
6. **SMS Support**: Twilio integration for critical alerts
7. **Push Notifications**: Mobile app push notifications
8. **Alert Rules**: User-defined alert conditions

## API Methods

### `send_alert()`

```python
async def send_alert(
    alert_type: str,
    ticker: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    channels: Optional[List[str]] = None,
    recipient: Optional[str] = None
) -> Dict[str, Any]
```

### `create_signal_alert()`

```python
async def create_signal_alert(
    signal_data: Dict[str, Any],
    channels: Optional[List[str]] = None,
    recipient: Optional[str] = None
) -> Dict[str, Any]
```

### `subscribe_user()`

```python
async def subscribe_user(
    user_id: str,
    alert_types: List[str],
    channels: List[str],
    recipient: Optional[str] = None
) -> Dict[str, Any]
```

### `get_alert_history()`

```python
async def get_alert_history(
    ticker: Optional[str] = None,
    limit: int = 100,
    alert_type: Optional[str] = None,
    channel: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]
```

### `get_pending_alerts()`

```python
async def get_pending_alerts() -> List[Dict[str, Any]]
```

### `mark_alert_delivered()`

```python
async def mark_alert_delivered(
    alert_id: int,
    status: str = "SENT"
) -> bool
```

## Testing

Run the example script to test the alert service:

```bash
cd backend
python -m app.services.alert_service_example
```

Make sure to configure SMTP and Slack settings first, or use only IN_APP channel for testing.

## Logging

The service uses loguru for structured logging:

- Info logs for successful deliveries
- Warning logs for configuration issues
- Error logs for delivery failures
- Debug logs for detailed troubleshooting

All logs include ticker, alert type, and channel information for easy filtering.
