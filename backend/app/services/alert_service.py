"""Alert delivery service for sending trading alerts via multiple channels"""

import smtplib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx
from loguru import logger
from sqlalchemy import select, and_, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.alert import AlertLog
from app.models.signal import Signal
from app.db.database import AsyncSessionLocal
from app.core.config import settings


class AlertChannel:
    """Alert delivery channels"""
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    SLACK = "SLACK"
    WEBHOOK = "WEBHOOK"


class AlertType:
    """Alert types"""
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    EXTREME_FLOW = "EXTREME_FLOW"
    COT_EXTREME = "COT_EXTREME"
    SQUEEZE_WARNING = "SQUEEZE_WARNING"
    SENTIMENT_SPIKE = "SENTIMENT_SPIKE"
    PRICE_ALERT = "PRICE_ALERT"


class AlertStatus:
    """Alert delivery status"""
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class AlertService:
    """Service for managing and delivering alerts across multiple channels"""

    def __init__(self):
        self.cooldown_config = {
            # Signal alerts: 1 hour cooldown (default)
            AlertType.SIGNAL_GENERATED: settings.ALERT_COOLDOWN_MINUTES,
            # Extreme conditions: 24 hour cooldown
            AlertType.EXTREME_FLOW: settings.ALERT_EXTREME_COOLDOWN_MINUTES,
            AlertType.COT_EXTREME: settings.ALERT_EXTREME_COOLDOWN_MINUTES,
            AlertType.SQUEEZE_WARNING: settings.ALERT_EXTREME_COOLDOWN_MINUTES,
            # Sentiment spikes: 1 hour cooldown
            AlertType.SENTIMENT_SPIKE: settings.ALERT_COOLDOWN_MINUTES,
            # Price alerts: 1 hour cooldown
            AlertType.PRICE_ALERT: settings.ALERT_COOLDOWN_MINUTES,
        }

    async def send_alert(
        self,
        alert_type: str,
        ticker: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[str]] = None,
        recipient: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an alert through specified channels

        Args:
            alert_type: Type of alert (e.g., SIGNAL_GENERATED)
            ticker: ETF ticker symbol
            message: Alert message text
            data: Additional data to include in alert
            channels: List of delivery channels (defaults to [IN_APP])
            recipient: Email/Slack recipient (required for EMAIL/SLACK channels)

        Returns:
            Dictionary with delivery status for each channel
        """
        if channels is None:
            channels = [AlertChannel.IN_APP]

        # Check if alert is in cooldown period
        if await self._is_in_cooldown(alert_type, ticker):
            logger.info(f"Alert {alert_type} for {ticker} is in cooldown, skipping")
            return {"status": "skipped", "reason": "cooldown"}

        results = {}

        for channel in channels:
            try:
                if channel == AlertChannel.IN_APP:
                    result = await self._send_in_app(alert_type, ticker, message, data)
                elif channel == AlertChannel.EMAIL:
                    if not recipient:
                        logger.warning(f"No recipient specified for EMAIL alert")
                        result = {"status": AlertStatus.FAILED, "error": "No recipient"}
                    else:
                        result = await self._send_email(alert_type, ticker, message, data, recipient)
                elif channel == AlertChannel.SLACK:
                    result = await self._send_slack(alert_type, ticker, message, data)
                elif channel == AlertChannel.WEBHOOK:
                    if not recipient:  # recipient holds webhook URL
                        logger.warning(f"No webhook URL specified")
                        result = {"status": AlertStatus.FAILED, "error": "No webhook URL"}
                    else:
                        result = await self._send_webhook(alert_type, ticker, message, data, recipient)
                else:
                    logger.warning(f"Unknown channel: {channel}")
                    result = {"status": AlertStatus.FAILED, "error": f"Unknown channel: {channel}"}

                results[channel] = result

            except Exception as e:
                logger.error(f"Error sending alert via {channel}: {e}")
                results[channel] = {"status": AlertStatus.FAILED, "error": str(e)}

        return results

    async def create_signal_alert(
        self,
        signal_data: Dict[str, Any],
        channels: Optional[List[str]] = None,
        recipient: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an alert from a trading signal

        Args:
            signal_data: Signal dictionary (from SignalGeneratorService)
            channels: Delivery channels
            recipient: Email/webhook recipient

        Returns:
            Alert delivery results
        """
        ticker = signal_data.get("ticker")
        signal_type = signal_data.get("signal_type")
        direction = signal_data.get("direction")
        strength = signal_data.get("strength", 0)
        notes = signal_data.get("notes", "")
        trigger_values = signal_data.get("trigger_values", {})

        # Format the alert message
        message = self._format_signal_message(
            ticker=ticker,
            signal_type=signal_type,
            direction=direction,
            strength=strength,
            notes=notes,
            trigger_values=trigger_values
        )

        data = {
            "signal_type": signal_type,
            "direction": direction,
            "strength": float(strength),
            "trigger_values": trigger_values,
            "expires_at": signal_data.get("expires_at").isoformat() if signal_data.get("expires_at") else None
        }

        return await self.send_alert(
            alert_type=AlertType.SIGNAL_GENERATED,
            ticker=ticker,
            message=message,
            data=data,
            channels=channels,
            recipient=recipient
        )

    async def subscribe_user(
        self,
        user_id: str,
        alert_types: List[str],
        channels: List[str],
        recipient: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Subscribe a user to specific alert types and channels

        Note: This is a simplified implementation. In production, you would
        store subscriptions in a database table.

        Args:
            user_id: User identifier
            alert_types: List of alert types to subscribe to
            channels: List of delivery channels
            recipient: Email or webhook URL

        Returns:
            Subscription confirmation
        """
        # TODO: In production, store this in a user_subscriptions table
        # For now, we'll just validate and return the subscription data
        subscription = {
            "user_id": user_id,
            "alert_types": alert_types,
            "channels": channels,
            "recipient": recipient,
            "created_at": datetime.now().isoformat(),
            "active": True
        }

        logger.info(f"User {user_id} subscribed to alerts: {alert_types} via {channels}")

        return {
            "status": "success",
            "subscription": subscription,
            "note": "Subscription preferences stored (in-memory for now)"
        }

    async def get_alert_history(
        self,
        ticker: Optional[str] = None,
        limit: int = 100,
        alert_type: Optional[str] = None,
        channel: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alert history with optional filters

        Args:
            ticker: Filter by ticker (optional)
            limit: Maximum number of alerts to return
            alert_type: Filter by alert type (optional)
            channel: Filter by channel (optional)
            status: Filter by status (optional)

        Returns:
            List of alert records
        """
        try:
            async with AsyncSessionLocal() as session:
                # Build query with filters
                query = select(AlertLog).order_by(AlertLog.sent_at.desc())

                conditions = []
                if ticker:
                    conditions.append(AlertLog.ticker == ticker)
                if alert_type:
                    conditions.append(AlertLog.alert_type == alert_type)
                if channel:
                    conditions.append(AlertLog.channel == channel)
                if status:
                    conditions.append(AlertLog.status == status)

                if conditions:
                    query = query.where(and_(*conditions))

                query = query.limit(limit)

                result = await session.execute(query)
                alerts = result.scalars().all()

                return [
                    {
                        "id": alert.id,
                        "sent_at": alert.sent_at.isoformat() if alert.sent_at else None,
                        "alert_type": alert.alert_type,
                        "ticker": alert.ticker,
                        "channel": alert.channel,
                        "recipient": alert.recipient,
                        "message": alert.message,
                        "status": alert.status,
                        "error_message": alert.error_message,
                        "created_at": alert.created_at.isoformat() if alert.created_at else None
                    }
                    for alert in alerts
                ]

        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            return []

    async def get_pending_alerts(self) -> List[Dict[str, Any]]:
        """
        Get all alerts that haven't been delivered yet

        Returns:
            List of pending alert records
        """
        return await self.get_alert_history(status=AlertStatus.PENDING)

    async def mark_alert_delivered(self, alert_id: int, status: str = AlertStatus.SENT) -> bool:
        """
        Mark an alert as delivered (or failed)

        Args:
            alert_id: Alert ID
            status: New status (SENT or FAILED)

        Returns:
            True if successful, False otherwise
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(AlertLog).where(AlertLog.id == alert_id)
                )
                alert = result.scalar_one_or_none()

                if not alert:
                    logger.warning(f"Alert {alert_id} not found")
                    return False

                alert.status = status
                alert.sent_at = datetime.now()

                await session.commit()
                logger.info(f"Alert {alert_id} marked as {status}")
                return True

        except Exception as e:
            logger.error(f"Error marking alert {alert_id} as delivered: {e}")
            return False

    # ========================================================================
    # PRIVATE METHODS - Channel Implementations
    # ========================================================================

    async def _send_in_app(
        self,
        alert_type: str,
        ticker: str,
        message: str,
        data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Store alert in database for in-app display

        Args:
            alert_type: Type of alert
            ticker: Ticker symbol
            message: Alert message
            data: Additional data

        Returns:
            Delivery result
        """
        try:
            async with AsyncSessionLocal() as session:
                alert = AlertLog(
                    alert_type=alert_type,
                    ticker=ticker,
                    channel=AlertChannel.IN_APP,
                    message=message,
                    status=AlertStatus.SENT,
                    sent_at=datetime.now()
                )

                session.add(alert)
                await session.commit()

                logger.info(f"IN_APP alert created for {ticker}: {alert_type}")

                return {
                    "status": AlertStatus.SENT,
                    "alert_id": alert.id,
                    "channel": AlertChannel.IN_APP
                }

        except Exception as e:
            logger.error(f"Error creating IN_APP alert: {e}")
            return {
                "status": AlertStatus.FAILED,
                "error": str(e),
                "channel": AlertChannel.IN_APP
            }

    async def _send_email(
        self,
        alert_type: str,
        ticker: str,
        message: str,
        data: Optional[Dict[str, Any]],
        recipient: str
    ) -> Dict[str, Any]:
        """
        Send alert via email using SMTP

        Args:
            alert_type: Type of alert
            ticker: Ticker symbol
            message: Alert message
            data: Additional data
            recipient: Email address

        Returns:
            Delivery result
        """
        alert_log_id = None

        try:
            # Create alert log record first
            async with AsyncSessionLocal() as session:
                alert = AlertLog(
                    alert_type=alert_type,
                    ticker=ticker,
                    channel=AlertChannel.EMAIL,
                    recipient=recipient,
                    message=message,
                    status=AlertStatus.PENDING
                )

                session.add(alert)
                await session.commit()
                alert_log_id = alert.id

            # Check if SMTP is configured
            if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
                error = "SMTP not configured"
                logger.warning(error)
                if alert_log_id:
                    await self._update_alert_status(alert_log_id, AlertStatus.FAILED, error)
                return {"status": AlertStatus.FAILED, "error": error}

            # Create email
            subject = f"[Commodity ETF Tracker] {alert_type}: {ticker}"
            body = self._format_email_body(alert_type, ticker, message, data)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = recipient

            # Add plain text and HTML parts
            text_part = MIMEText(body, "plain")
            html_part = MIMEText(self._format_email_html(alert_type, ticker, message, data), "html")

            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email sent to {recipient} for {ticker}: {alert_type}")

            # Update alert status
            if alert_log_id:
                await self._update_alert_status(alert_log_id, AlertStatus.SENT)

            return {
                "status": AlertStatus.SENT,
                "alert_id": alert_log_id,
                "channel": AlertChannel.EMAIL,
                "recipient": recipient
            }

        except Exception as e:
            error = str(e)
            logger.error(f"Error sending email to {recipient}: {error}")

            if alert_log_id:
                await self._update_alert_status(alert_log_id, AlertStatus.FAILED, error)

            return {
                "status": AlertStatus.FAILED,
                "error": error,
                "channel": AlertChannel.EMAIL
            }

    async def _send_slack(
        self,
        alert_type: str,
        ticker: str,
        message: str,
        data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send alert via Slack webhook

        Args:
            alert_type: Type of alert
            ticker: Ticker symbol
            message: Alert message
            data: Additional data

        Returns:
            Delivery result
        """
        alert_log_id = None

        try:
            # Create alert log record first
            async with AsyncSessionLocal() as session:
                alert = AlertLog(
                    alert_type=alert_type,
                    ticker=ticker,
                    channel=AlertChannel.SLACK,
                    recipient="slack_webhook",
                    message=message,
                    status=AlertStatus.PENDING
                )

                session.add(alert)
                await session.commit()
                alert_log_id = alert.id

            # Check if Slack webhook is configured
            if not settings.SLACK_WEBHOOK_URL:
                error = "Slack webhook not configured"
                logger.warning(error)
                if alert_log_id:
                    await self._update_alert_status(alert_log_id, AlertStatus.FAILED, error)
                return {"status": AlertStatus.FAILED, "error": error}

            # Format Slack message
            slack_message = self._format_slack_message(alert_type, ticker, message, data)

            # Send to Slack
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.SLACK_WEBHOOK_URL,
                    json=slack_message,
                    timeout=10.0
                )
                response.raise_for_status()

            logger.info(f"Slack alert sent for {ticker}: {alert_type}")

            # Update alert status
            if alert_log_id:
                await self._update_alert_status(alert_log_id, AlertStatus.SENT)

            return {
                "status": AlertStatus.SENT,
                "alert_id": alert_log_id,
                "channel": AlertChannel.SLACK
            }

        except Exception as e:
            error = str(e)
            logger.error(f"Error sending Slack alert: {error}")

            if alert_log_id:
                await self._update_alert_status(alert_log_id, AlertStatus.FAILED, error)

            return {
                "status": AlertStatus.FAILED,
                "error": error,
                "channel": AlertChannel.SLACK
            }

    async def _send_webhook(
        self,
        alert_type: str,
        ticker: str,
        message: str,
        data: Optional[Dict[str, Any]],
        webhook_url: str
    ) -> Dict[str, Any]:
        """
        Send alert via generic webhook

        Args:
            alert_type: Type of alert
            ticker: Ticker symbol
            message: Alert message
            data: Additional data
            webhook_url: Webhook URL

        Returns:
            Delivery result
        """
        alert_log_id = None

        try:
            # Create alert log record first
            async with AsyncSessionLocal() as session:
                alert = AlertLog(
                    alert_type=alert_type,
                    ticker=ticker,
                    channel=AlertChannel.WEBHOOK,
                    recipient=webhook_url,
                    message=message,
                    status=AlertStatus.PENDING
                )

                session.add(alert)
                await session.commit()
                alert_log_id = alert.id

            # Format webhook payload
            payload = {
                "alert_type": alert_type,
                "ticker": ticker,
                "message": message,
                "data": data or {},
                "timestamp": datetime.now().isoformat()
            }

            # Send to webhook
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()

            logger.info(f"Webhook alert sent to {webhook_url} for {ticker}: {alert_type}")

            # Update alert status
            if alert_log_id:
                await self._update_alert_status(alert_log_id, AlertStatus.SENT)

            return {
                "status": AlertStatus.SENT,
                "alert_id": alert_log_id,
                "channel": AlertChannel.WEBHOOK,
                "recipient": webhook_url
            }

        except Exception as e:
            error = str(e)
            logger.error(f"Error sending webhook alert to {webhook_url}: {error}")

            if alert_log_id:
                await self._update_alert_status(alert_log_id, AlertStatus.FAILED, error)

            return {
                "status": AlertStatus.FAILED,
                "error": error,
                "channel": AlertChannel.WEBHOOK
            }

    # ========================================================================
    # PRIVATE METHODS - Utilities
    # ========================================================================

    async def _is_in_cooldown(self, alert_type: str, ticker: str) -> bool:
        """
        Check if an alert is in cooldown period

        Args:
            alert_type: Type of alert
            ticker: Ticker symbol

        Returns:
            True if in cooldown, False otherwise
        """
        try:
            cooldown_minutes = self.cooldown_config.get(alert_type, settings.ALERT_COOLDOWN_MINUTES)
            cooldown_threshold = datetime.now() - timedelta(minutes=cooldown_minutes)

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(AlertLog)
                    .where(
                        and_(
                            AlertLog.alert_type == alert_type,
                            AlertLog.ticker == ticker,
                            AlertLog.status == AlertStatus.SENT,
                            AlertLog.sent_at >= cooldown_threshold
                        )
                    )
                    .limit(1)
                )

                recent_alert = result.scalar_one_or_none()
                return recent_alert is not None

        except Exception as e:
            logger.error(f"Error checking cooldown: {e}")
            return False

    async def _update_alert_status(
        self,
        alert_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update alert status in database

        Args:
            alert_id: Alert ID
            status: New status
            error_message: Error message if failed
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(AlertLog).where(AlertLog.id == alert_id)
                )
                alert = result.scalar_one_or_none()

                if alert:
                    alert.status = status
                    alert.sent_at = datetime.now()
                    if error_message:
                        alert.error_message = error_message

                    await session.commit()

        except Exception as e:
            logger.error(f"Error updating alert status: {e}")

    def _format_signal_message(
        self,
        ticker: str,
        signal_type: str,
        direction: str,
        strength: float,
        notes: str,
        trigger_values: Dict[str, Any]
    ) -> str:
        """
        Format a signal into an alert message

        Args:
            ticker: Ticker symbol
            signal_type: Signal type
            direction: BUY/SELL/WATCH
            strength: Signal strength (0-1)
            notes: Signal notes
            trigger_values: Signal trigger values

        Returns:
            Formatted message string
        """
        strength_pct = int(strength * 100)

        message = f"🔔 {signal_type} Signal for {ticker}\n\n"
        message += f"Direction: {direction}\n"
        message += f"Strength: {strength_pct}%\n\n"
        message += f"{notes}\n\n"

        # Add key metrics
        if trigger_values:
            message += "Key Metrics:\n"
            for key, value in trigger_values.items():
                if isinstance(value, float):
                    message += f"  • {key}: {value:.2f}\n"
                else:
                    message += f"  • {key}: {value}\n"

        return message

    def _format_email_body(
        self,
        alert_type: str,
        ticker: str,
        message: str,
        data: Optional[Dict[str, Any]]
    ) -> str:
        """
        Format plain text email body

        Args:
            alert_type: Type of alert
            ticker: Ticker symbol
            message: Alert message
            data: Additional data

        Returns:
            Formatted email body
        """
        body = f"Commodity ETF Tracker Alert\n"
        body += f"{'=' * 50}\n\n"
        body += f"Alert Type: {alert_type}\n"
        body += f"Ticker: {ticker}\n"
        body += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        body += f"{'=' * 50}\n\n"
        body += message
        body += f"\n\n{'=' * 50}\n"
        body += f"\nThis is an automated alert from Commodity ETF Tracker.\n"

        return body

    def _format_email_html(
        self,
        alert_type: str,
        ticker: str,
        message: str,
        data: Optional[Dict[str, Any]]
    ) -> str:
        """
        Format HTML email body

        Args:
            alert_type: Type of alert
            ticker: Ticker symbol
            message: Alert message
            data: Additional data

        Returns:
            Formatted HTML email body
        """
        html = f"""
        <html>
          <head>
            <style>
              body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
              .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
              .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
              .content {{ background-color: #f9f9f9; padding: 20px; margin: 20px 0; }}
              .alert-type {{ font-size: 18px; font-weight: bold; color: #e74c3c; }}
              .ticker {{ font-size: 24px; font-weight: bold; color: #3498db; }}
              .message {{ white-space: pre-wrap; margin: 20px 0; }}
              .footer {{ text-align: center; color: #7f8c8d; font-size: 12px; margin-top: 20px; }}
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>Commodity ETF Tracker</h1>
              </div>
              <div class="content">
                <p class="alert-type">{alert_type}</p>
                <p class="ticker">{ticker}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <hr>
                <div class="message">{message}</div>
              </div>
              <div class="footer">
                <p>This is an automated alert from Commodity ETF Tracker.</p>
              </div>
            </div>
          </body>
        </html>
        """
        return html

    def _format_slack_message(
        self,
        alert_type: str,
        ticker: str,
        message: str,
        data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Format Slack message payload

        Args:
            alert_type: Type of alert
            ticker: Ticker symbol
            message: Alert message
            data: Additional data

        Returns:
            Slack message payload
        """
        # Determine color based on direction (if available in data)
        color = "#3498db"  # Default blue
        if data:
            direction = data.get("direction")
            if direction == "BUY":
                color = "#2ecc71"  # Green
            elif direction == "SELL":
                color = "#e74c3c"  # Red
            elif direction == "WATCH":
                color = "#f39c12"  # Orange

        return {
            "text": f"🔔 {alert_type}: {ticker}",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Alert Type",
                            "value": alert_type,
                            "short": True
                        },
                        {
                            "title": "Ticker",
                            "value": ticker,
                            "short": True
                        }
                    ],
                    "text": message,
                    "footer": "Commodity ETF Tracker",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }


# Global instance
alert_service = AlertService()
