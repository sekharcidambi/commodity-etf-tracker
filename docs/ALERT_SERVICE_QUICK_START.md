# Alert Service Quick Start Guide

## Files Created

1. **`/backend/app/models/alert.py`** - AlertLog database model
2. **`/backend/app/services/alert_service.py`** - Main alert service (891 lines)
3. **`/backend/app/services/alert_service_example.py`** - Usage examples
4. **Updated `/backend/app/core/config.py`** - Added alert configuration settings
5. **Updated `/backend/app/models/__init__.py`** - Exported AlertLog model

## Quick Setup

### 1. Configure Environment Variables

Add to your `.env` file:

```bash
# Email Alerts (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=alerts@commodity-tracker.com
SMTP_FROM_NAME=Commodity ETF Tracker

# Slack Alerts (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Cooldown Settings
ALERT_COOLDOWN_MINUTES=60
ALERT_EXTREME_COOLDOWN_MINUTES=1440
```

### 2. Basic Usage

```python
from app.services.alert_service import alert_service, AlertChannel, AlertType

# Send a simple in-app alert
result = await alert_service.send_alert(
    alert_type=AlertType.SIGNAL_GENERATED,
    ticker="AGQ",
    message="Buy signal detected",
    channels=[AlertChannel.IN_APP]
)
```

### 3. Send Signal Alert

```python
# After generating a signal
from app.services.signal_generator import SignalGeneratorService

signal_gen = SignalGeneratorService()
signals = await signal_gen.generate_signals("AGQ")

# Send alert for each signal
for signal in signals:
    await alert_service.create_signal_alert(
        signal_data=signal,
        channels=[AlertChannel.IN_APP, AlertChannel.EMAIL],
        recipient="trader@example.com"
    )
```

### 4. Get Alert History

```python
# Get recent alerts
alerts = await alert_service.get_alert_history(
    ticker="AGQ",
    limit=50
)

for alert in alerts:
    print(f"{alert['sent_at']}: {alert['alert_type']} - {alert['status']}")
```

## Supported Channels

1. **IN_APP** - Stores in database, no external config needed
2. **EMAIL** - Requires SMTP configuration
3. **SLACK** - Requires webhook URL
4. **WEBHOOK** - Generic HTTP POST to any URL

## Supported Alert Types

1. **SIGNAL_GENERATED** - New trading signal (1h cooldown)
2. **EXTREME_FLOW** - Extreme flow detected (24h cooldown)
3. **COT_EXTREME** - COT positioning extreme (24h cooldown)
4. **SQUEEZE_WARNING** - Inventory squeeze (24h cooldown)
5. **SENTIMENT_SPIKE** - Retail activity spike (1h cooldown)
6. **PRICE_ALERT** - Price threshold crossed (1h cooldown)

## Key Features

- **Multi-channel delivery** - Send to IN_APP, EMAIL, SLACK, or WEBHOOK
- **Alert deduplication** - Prevents spam with configurable cooldowns
- **Comprehensive logging** - All alerts tracked in `alert_log` table
- **Professional formatting** - HTML emails, Slack blocks
- **Error handling** - Failed alerts logged with error messages
- **History & tracking** - Query past alerts with filters

## Testing

Run the examples:

```bash
cd /home/user/commodity-etf-tracker/backend
python -m app.services.alert_service_example
```

## Database Table

The `alert_log` table is already created in your schema:

```sql
id, sent_at, alert_type, ticker, channel, recipient,
message, status, error_message, created_at
```

Status values: `PENDING`, `SENT`, `FAILED`

## Next Steps

1. Configure SMTP/Slack credentials in `.env`
2. Test with IN_APP channel (no config needed)
3. Integrate with SignalGeneratorService
4. Create API endpoints for frontend alert display
5. Implement user subscription preferences table

## Common Patterns

### Send alert to multiple channels

```python
await alert_service.send_alert(
    alert_type=AlertType.EXTREME_FLOW,
    ticker="AGQ",
    message="Extreme inflow detected",
    channels=[
        AlertChannel.IN_APP,
        AlertChannel.EMAIL,
        AlertChannel.SLACK
    ],
    recipient="trader@example.com"
)
```

### Filter alerts by status

```python
# Get only failed alerts
failed = await alert_service.get_alert_history(
    status="FAILED",
    limit=100
)
```

### Retry failed alert

```python
# Mark as delivered after manual retry
await alert_service.mark_alert_delivered(
    alert_id=123,
    status="SENT"
)
```

## Full Documentation

See `/home/user/commodity-etf-tracker/docs/ALERT_SERVICE.md` for complete documentation.
