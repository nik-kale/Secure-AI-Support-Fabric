"""
Notification Service (V4.2)
Multi-channel notifications (Slack, Teams, Email, Webhooks)
"""
import os
import sys
import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, List, Any, Optional
import threading
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lab.common.logging_config import setup_logging
from lab.common.auth import require_auth, setup_auth_error_handlers
from lab.common.security_headers import setup_security_headers
from lab.common.rate_limit import rate_limit

logger = setup_logging('notification_service')

app = Flask(__name__)

# Security configurations
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB

# CORS
allowed_origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

# Setup security
setup_auth_error_handlers(app)
setup_security_headers(app)


class NotificationChannel:
    """Base class for notification channels"""

    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.retry_count = config.get('retry_count', 3)
        self.timeout = config.get('timeout', 10)

    def send(self, message: Dict) -> bool:
        """Send notification (to be implemented by subclasses)"""
        raise NotImplementedError


class SlackChannel(NotificationChannel):
    """Slack webhook notifications"""

    def __init__(self, name: str, config: Dict):
        super().__init__(name, config)
        self.webhook_url = config.get('webhook_url')
        if not self.webhook_url:
            logger.warning(f"Slack channel '{name}' missing webhook_url")
            self.enabled = False

    def send(self, message: Dict) -> bool:
        """Send to Slack"""
        if not self.enabled:
            return False

        try:
            # Build Slack message
            slack_payload = {
                "text": message.get('title', 'Notification'),
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": message.get('title', 'Alert')
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message.get('body', '')
                        }
                    }
                ]
            }

            # Add severity color
            severity = message.get('severity', 'INFO')
            color_map = {
                'CRITICAL': '#D32F2F',
                'ERROR': '#F57C00',
                'WARNING': '#FBC02D',
                'INFO': '#1976D2',
                'LOW': '#388E3C'
            }

            if severity in color_map:
                slack_payload['attachments'] = [{
                    "color": color_map[severity],
                    "fields": [
                        {
                            "title": "Severity",
                            "value": severity,
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": message.get('timestamp', datetime.utcnow().isoformat()),
                            "short": True
                        }
                    ]
                }]

            # Add metadata fields if present
            if message.get('fields'):
                fields = []
                for key, value in message['fields'].items():
                    fields.append({
                        "title": key,
                        "value": str(value),
                        "short": True
                    })
                if 'attachments' in slack_payload:
                    slack_payload['attachments'][0]['fields'].extend(fields)

            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=slack_payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.info(f"Sent notification to Slack channel '{self.name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}", exc_info=True)
            return False


class TeamsChannel(NotificationChannel):
    """Microsoft Teams webhook notifications"""

    def __init__(self, name: str, config: Dict):
        super().__init__(name, config)
        self.webhook_url = config.get('webhook_url')
        if not self.webhook_url:
            logger.warning(f"Teams channel '{name}' missing webhook_url")
            self.enabled = False

    def send(self, message: Dict) -> bool:
        """Send to Microsoft Teams"""
        if not self.enabled:
            return False

        try:
            # Build Teams adaptive card
            teams_payload = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": message.get('title', 'Notification'),
                "themeColor": self._get_color(message.get('severity', 'INFO')),
                "title": message.get('title', 'Alert'),
                "sections": [
                    {
                        "text": message.get('body', ''),
                        "facts": [
                            {
                                "name": "Severity",
                                "value": message.get('severity', 'INFO')
                            },
                            {
                                "name": "Timestamp",
                                "value": message.get('timestamp', datetime.utcnow().isoformat())
                            }
                        ]
                    }
                ]
            }

            # Add custom fields
            if message.get('fields'):
                for key, value in message['fields'].items():
                    teams_payload['sections'][0]['facts'].append({
                        "name": key,
                        "value": str(value)
                    })

            # Send to Teams
            response = requests.post(
                self.webhook_url,
                json=teams_payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.info(f"Sent notification to Teams channel '{self.name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}", exc_info=True)
            return False

    def _get_color(self, severity: str) -> str:
        """Get hex color for severity"""
        color_map = {
            'CRITICAL': 'D32F2F',
            'ERROR': 'F57C00',
            'WARNING': 'FBC02D',
            'INFO': '1976D2',
            'LOW': '388E3C'
        }
        return color_map.get(severity, '1976D2')


class WebhookChannel(NotificationChannel):
    """Generic webhook notifications"""

    def __init__(self, name: str, config: Dict):
        super().__init__(name, config)
        self.url = config.get('url')
        self.method = config.get('method', 'POST')
        self.headers = config.get('headers', {})

        if not self.url:
            logger.warning(f"Webhook channel '{name}' missing url")
            self.enabled = False

    def send(self, message: Dict) -> bool:
        """Send to webhook"""
        if not self.enabled:
            return False

        try:
            response = requests.request(
                method=self.method,
                url=self.url,
                json=message,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.info(f"Sent notification to webhook '{self.name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}", exc_info=True)
            return False


class EmailChannel(NotificationChannel):
    """Email notifications via SMTP"""

    def __init__(self, name: str, config: Dict):
        super().__init__(name, config)
        self.smtp_host = config.get('smtp_host')
        self.smtp_port = config.get('smtp_port', 587)
        self.smtp_user = config.get('smtp_user')
        self.smtp_password = config.get('smtp_password')
        self.from_email = config.get('from_email')
        self.to_emails = config.get('to_emails', [])

        if not all([self.smtp_host, self.smtp_user, self.smtp_password, self.from_email]):
            logger.warning(f"Email channel '{name}' missing required config")
            self.enabled = False

    def send(self, message: Dict) -> bool:
        """Send email"""
        if not self.enabled or not self.to_emails:
            return False

        try:
            # Build email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = message.get('title', 'Notification')
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)

            # HTML body
            html_body = f"""
            <html>
                <body>
                    <h2>{message.get('title', 'Notification')}</h2>
                    <p>{message.get('body', '')}</p>
                    <hr>
                    <p><strong>Severity:</strong> {message.get('severity', 'INFO')}</p>
                    <p><strong>Timestamp:</strong> {message.get('timestamp', datetime.utcnow().isoformat())}</p>
            """

            if message.get('fields'):
                html_body += "<h3>Additional Details:</h3><ul>"
                for key, value in message['fields'].items():
                    html_body += f"<li><strong>{key}:</strong> {value}</li>"
                html_body += "</ul>"

            html_body += "</body></html>"

            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Sent email notification to {len(self.to_emails)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}", exc_info=True)
            return False


class NotificationService:
    """Central notification service managing multiple channels"""

    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {}
        self.notification_history = deque(maxlen=1000)
        self._lock = threading.Lock()
        self._load_channels()

        logger.info("Notification service initialized")

    def _load_channels(self):
        """Load notification channels from config"""
        # Load from environment or config file
        # For now, we'll support dynamic channel registration via API

        # Example: Auto-register from environment
        slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        if slack_webhook:
            self.register_channel('slack_default', 'slack', {
                'webhook_url': slack_webhook,
                'enabled': True
            })

        teams_webhook = os.getenv('TEAMS_WEBHOOK_URL')
        if teams_webhook:
            self.register_channel('teams_default', 'teams', {
                'webhook_url': teams_webhook,
                'enabled': True
            })

    def register_channel(self, name: str, channel_type: str, config: Dict) -> bool:
        """Register a notification channel"""
        with self._lock:
            try:
                if channel_type == 'slack':
                    channel = SlackChannel(name, config)
                elif channel_type == 'teams':
                    channel = TeamsChannel(name, config)
                elif channel_type == 'webhook':
                    channel = WebhookChannel(name, config)
                elif channel_type == 'email':
                    channel = EmailChannel(name, config)
                else:
                    logger.error(f"Unknown channel type: {channel_type}")
                    return False

                self.channels[name] = channel
                logger.info(f"Registered {channel_type} channel: {name}")
                return True

            except Exception as e:
                logger.error(f"Failed to register channel: {e}", exc_info=True)
                return False

    def send_notification(self, message: Dict, channels: List[str] = None) -> Dict:
        """
        Send notification to specified channels (or all if not specified)

        Args:
            message: {
                'title': str,
                'body': str,
                'severity': str (CRITICAL/ERROR/WARNING/INFO/LOW),
                'timestamp': str (ISO format),
                'fields': dict (optional additional fields)
            }
            channels: List of channel names (None = all channels)

        Returns:
            Dict with success status per channel
        """
        results = {}

        target_channels = channels or list(self.channels.keys())

        for channel_name in target_channels:
            if channel_name not in self.channels:
                results[channel_name] = {
                    'success': False,
                    'error': 'Channel not found'
                }
                continue

            channel = self.channels[channel_name]
            if not channel.enabled:
                results[channel_name] = {
                    'success': False,
                    'error': 'Channel disabled'
                }
                continue

            success = channel.send(message)
            results[channel_name] = {
                'success': success
            }

        # Store in history
        self.notification_history.append({
            'message': message,
            'channels': target_channels,
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        })

        return results

    def get_channels(self) -> List[Dict]:
        """Get all registered channels"""
        return [
            {
                'name': name,
                'type': channel.__class__.__name__.replace('Channel', '').lower(),
                'enabled': channel.enabled
            }
            for name, channel in self.channels.items()
        ]

    def get_history(self, limit: int = 100) -> List[Dict]:
        """Get notification history"""
        return list(self.notification_history)[-limit:]


# Initialize service
notification_service = NotificationService()


# ===================================================================
# API ENDPOINTS
# ===================================================================

@app.route('/api/notifications/send', methods=['POST'])
@rate_limit(tier='notification', max_requests=1000, window_seconds=3600)
@require_auth
def send_notification():
    """Send notification to channels"""
    try:
        data = request.json

        message = {
            'title': data.get('title', 'Notification'),
            'body': data.get('body', ''),
            'severity': data.get('severity', 'INFO'),
            'timestamp': data.get('timestamp', datetime.utcnow().isoformat()),
            'fields': data.get('fields', {})
        }

        channels = data.get('channels')  # None = all channels

        results = notification_service.send_notification(message, channels)

        return jsonify({
            'success': True,
            'results': results
        }), 200

    except Exception as e:
        logger.error(f"Failed to send notification: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to send notification'
        }), 500


@app.route('/api/notifications/channels', methods=['GET'])
@rate_limit(tier='query', max_requests=100, window_seconds=3600)
@require_auth
def get_channels():
    """Get all notification channels"""
    try:
        channels = notification_service.get_channels()

        return jsonify({
            'success': True,
            'channels': channels
        }), 200

    except Exception as e:
        logger.error(f"Failed to get channels: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve channels'
        }), 500


@app.route('/api/notifications/channels/register', methods=['POST'])
@rate_limit(tier='admin', max_requests=100, window_seconds=3600)
@require_auth
def register_channel():
    """Register a new notification channel"""
    try:
        data = request.json

        name = data.get('name')
        channel_type = data.get('type')
        config = data.get('config', {})

        if not name or not channel_type:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: name, type'
            }), 400

        success = notification_service.register_channel(name, channel_type, config)

        return jsonify({
            'success': success
        }), 200 if success else 500

    except Exception as e:
        logger.error(f"Failed to register channel: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to register channel'
        }), 500


@app.route('/api/notifications/history', methods=['GET'])
@rate_limit(tier='query', max_requests=100, window_seconds=3600)
@require_auth
def get_history():
    """Get notification history"""
    try:
        limit = int(request.args.get('limit', 100))

        history = notification_service.get_history(limit)

        return jsonify({
            'success': True,
            'count': len(history),
            'history': history
        }), 200

    except Exception as e:
        logger.error(f"Failed to get history: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve history'
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'notification_service',
        'channels': len(notification_service.channels),
        'timestamp': datetime.utcnow().isoformat()
    }), 200


if __name__ == '__main__':
    logger.info("Starting Notification Service on port 8087")
    app.run(
        host='0.0.0.0',
        port=8087,
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
