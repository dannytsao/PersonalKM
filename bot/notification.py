#!/usr/bin/env python3
"""
Ingestion Monitoring Script
Sends notification when weekly ingestion runs (success or failure)
Supports multiple notification methods: LINE, Discord webhook, email, or file-based
"""
import json
import logging
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Notification configuration
NOTIFY_LINE = os.getenv("NOTIFY_LINE_WEBHOOK", "")
NOTIFY_DISCORD = os.getenv("NOTIFY_DISCORD_WEBHOOK", "")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "")
NOTIFY_FILE = os.getenv("NOTIFY_FILE", "")  # Path to write notification file


def send_line_notification(message: str) -> bool:
    """Send notification via LINE Messaging API."""
    if not NOTIFY_LINE:
        return False
    try:
        import urllib.request
        import urllib.error

        data = json.dumps({"messages": [{"type": "text", "text": message}]}).encode()
        req = urllib.request.Request(
            NOTIFY_LINE,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception as e:
        logger.error(f"LINE notification failed: {e}")
        return False


def send_discord_notification(message: str, color: int = 0x00FF00) -> bool:
    """Send notification via Discord webhook."""
    if not NOTIFY_DISCORD:
        return False
    try:
        import urllib.request

        data = json.dumps({
            "embeds": [{
                "title": "PersonalKM Ingestion Report",
                "description": message,
                "color": color,
                "timestamp": datetime.now().isoformat()
            }]
        }).encode()
        req = urllib.request.Request(
            NOTIFY_DISCORD,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception as e:
        logger.error(f"Discord notification failed: {e}")
        return False


def send_file_notification(message: str, status: str) -> bool:
    """Write notification to a file."""
    if not NOTIFY_FILE:
        return False
    try:
        with open(NOTIFY_FILE, "w") as f:
            f.write(f"Status: {status}\n")
            f.write(f"Time: {datetime.now().isoformat()}\n")
            f.write(f"Message: {message}\n")
        return True
    except Exception as e:
        logger.error(f"File notification failed: {e}")
        return False


def send_email_notification(message: str) -> bool:
    """Send email notification via sendmail or SMTP."""
    if not NOTIFY_EMAIL:
        return False
    try:
        import subprocess
        cmd = f"echo '{message}' | mail -s 'PersonalKM Ingestion Report' {NOTIFY_EMAIL}"
        subprocess.run(cmd, shell=True, check=False)
        return True
    except Exception as e:
        logger.error(f"Email notification failed: {e}")
        return False


def notify(title: str, message: str, success: bool = True) -> None:
    """
    Send notification via all configured methods.

    Args:
        title: Notification title
        message: Notification body
        success: If True, use green/success color; if False, use red/error color
    """
    color = 0x00FF00 if success else 0xFF0000
    status = "✅ SUCCESS" if success else "❌ FAILED"

    full_message = f"{status}\n\n{title}\n\n{message}"

    # Send to all configured channels
    results = {
        "LINE": send_line_notification(full_message),
        "Discord": send_discord_notification(message, color),
        "Email": send_email_notification(message),
        "File": send_file_notification(message, status)
    }

    # Log results
    for channel, sent in results.items():
        if sent:
            logger.info(f"✅ Notification sent via {channel}")
        elif results[channel] is False:
            pass  # Not configured, skip
        else:
            logger.warning(f"⚠️  Failed to send via {channel}")


def notify_ingestion_start(vault_path: str, file_count: int) -> None:
    """Notify that ingestion has started."""
    notify(
        title="Weekly Ingestion Started",
        message=f"Processing {file_count} files from {vault_path}",
        success=True
    )


def notify_ingestion_success(
    vault_path: str,
    processed: int,
    failed: int,
    duration_seconds: float
) -> None:
    """Notify that ingestion completed successfully."""
    notify(
        title="✅ Weekly Ingestion Complete",
        message=(
            f"Processed: {processed} files\n"
            f"Failed: {failed} files\n"
            f"Duration: {duration_seconds:.1f} seconds\n"
            f"Vault: {vault_path}"
        ),
        success=True
    )


def notify_ingestion_failure(vault_path: str, error: str) -> None:
    """Notify that ingestion failed."""
    notify(
        title="❌ Weekly Ingestion FAILED",
        message=(
            f"Error: {error}\n"
            f"Vault: {vault_path}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ),
        success=False
    )


if __name__ == "__main__":
    # Test notification
    print("Testing notification system...")
    notify("Test", "This is a test notification", success=True)
    print("Done!")