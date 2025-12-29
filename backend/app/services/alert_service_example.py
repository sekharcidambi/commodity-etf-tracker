"""
Example usage of the AlertService

This file demonstrates how to use the alert delivery system
for sending trading alerts via multiple channels.
"""

import asyncio
from datetime import datetime, timedelta

from app.services.alert_service import alert_service, AlertChannel, AlertType


async def example_send_signal_alert():
    """Example: Send a signal-generated alert"""

    # Example signal data (typically from SignalGeneratorService)
    signal_data = {
        "ticker": "AGQ",
        "signal_type": "EXTREME_FLOW",
        "direction": "BUY",
        "strength": 0.85,
        "trigger_values": {
            "z_score": 2.45,
            "percentile": 98.2,
            "rolling_sum_4w": 125.3,
            "threshold": 2.0
        },
        "notes": "Extreme inflow detected (z-score: 2.45)",
        "expires_at": datetime.now() + timedelta(days=14)
    }

    # Send alert via IN_APP and EMAIL
    result = await alert_service.create_signal_alert(
        signal_data=signal_data,
        channels=[AlertChannel.IN_APP, AlertChannel.EMAIL],
        recipient="trader@example.com"
    )

    print(f"Signal alert sent: {result}")


async def example_send_custom_alert():
    """Example: Send a custom alert"""

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

    print(f"Custom alert sent: {result}")


async def example_extreme_flow_alert():
    """Example: Send extreme flow alert with webhook"""

    result = await alert_service.send_alert(
        alert_type=AlertType.EXTREME_FLOW,
        ticker="AGQ",
        message="Extreme inflow detected: $125M in 4 weeks (98th percentile)",
        data={
            "flow_4w": 125.3,
            "z_score": 2.45,
            "percentile": 98.2
        },
        channels=[AlertChannel.IN_APP, AlertChannel.WEBHOOK],
        recipient="https://your-webhook-endpoint.com/alerts"
    )

    print(f"Extreme flow alert sent: {result}")


async def example_cot_extreme_alert():
    """Example: Send COT extreme positioning alert"""

    result = await alert_service.send_alert(
        alert_type=AlertType.COT_EXTREME,
        ticker="UGL",
        message="COT: Extreme bullish positioning in gold (contrarian sell signal)",
        data={
            "commodity": "gold",
            "managed_money_net": 145000,
            "percentile": 95.8,
            "z_score": 2.3,
            "positioning_type": "extreme_bullish"
        },
        channels=[AlertChannel.IN_APP, AlertChannel.EMAIL, AlertChannel.SLACK],
        recipient="trader@example.com"
    )

    print(f"COT extreme alert sent: {result}")


async def example_get_alert_history():
    """Example: Retrieve alert history"""

    # Get all alerts for AGQ
    alerts = await alert_service.get_alert_history(ticker="AGQ", limit=50)
    print(f"\nFound {len(alerts)} alerts for AGQ:")
    for alert in alerts[:5]:  # Print first 5
        print(f"  - {alert['sent_at']}: {alert['alert_type']} via {alert['channel']} - {alert['status']}")

    # Get pending alerts
    pending = await alert_service.get_pending_alerts()
    print(f"\nFound {len(pending)} pending alerts")

    # Get only SIGNAL_GENERATED alerts
    signal_alerts = await alert_service.get_alert_history(
        alert_type=AlertType.SIGNAL_GENERATED,
        limit=20
    )
    print(f"\nFound {len(signal_alerts)} signal alerts")


async def example_subscribe_user():
    """Example: Subscribe a user to alerts"""

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

    print(f"User subscribed: {subscription}")


async def example_cooldown_behavior():
    """Example: Demonstrate cooldown behavior"""

    # First alert - should send
    result1 = await alert_service.send_alert(
        alert_type=AlertType.SIGNAL_GENERATED,
        ticker="AGQ",
        message="First alert",
        channels=[AlertChannel.IN_APP]
    )
    print(f"First alert: {result1}")

    # Second alert immediately after - should be in cooldown
    result2 = await alert_service.send_alert(
        alert_type=AlertType.SIGNAL_GENERATED,
        ticker="AGQ",
        message="Second alert (should be skipped)",
        channels=[AlertChannel.IN_APP]
    )
    print(f"Second alert (immediate): {result2}")

    # Different alert type - should send (different cooldown)
    result3 = await alert_service.send_alert(
        alert_type=AlertType.PRICE_ALERT,
        ticker="AGQ",
        message="Different alert type",
        channels=[AlertChannel.IN_APP]
    )
    print(f"Different alert type: {result3}")


async def example_mark_alert_delivered():
    """Example: Manually mark alert as delivered"""

    # Get a pending alert
    pending = await alert_service.get_pending_alerts()

    if pending:
        alert_id = pending[0]['id']
        success = await alert_service.mark_alert_delivered(alert_id, status="SENT")
        print(f"Marked alert {alert_id} as delivered: {success}")
    else:
        print("No pending alerts to mark")


async def main():
    """Run all examples"""

    print("=" * 60)
    print("Alert Service Examples")
    print("=" * 60)

    # Note: These examples assume SMTP/Slack are configured
    # For testing, you may want to use only IN_APP channel

    print("\n1. Signal Alert Example:")
    await example_send_signal_alert()

    print("\n2. Custom Alert Example:")
    await example_send_custom_alert()

    print("\n3. Extreme Flow Alert Example:")
    await example_extreme_flow_alert()

    print("\n4. COT Extreme Alert Example:")
    await example_cot_extreme_alert()

    print("\n5. Subscribe User Example:")
    await example_subscribe_user()

    print("\n6. Cooldown Behavior Example:")
    await example_cooldown_behavior()

    print("\n7. Alert History Example:")
    await example_get_alert_history()

    print("\n8. Mark Alert Delivered Example:")
    await example_mark_alert_delivered()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
