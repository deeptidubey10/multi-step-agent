"""EmailTool - Email sending wrapper (mock for now, easily upgradeable to SMTP)."""

from datetime import datetime
from typing import Any


class EmailTool:
    """Sends emails (mock implementation for testing, SMTP-ready for production)."""

    def __init__(self, log_path: str = "audit_logs/emails.log"):
        """Initialize email tool with optional file logging."""
        self.log_path = log_path
        self.sent_emails = []

    def send_email(self, to: str, subject: str, body: str) -> dict[str, Any]:
        """
        Send an email (currently mocked, prints to console and logs).

        Args:
            to: Recipient email address
            subject: Email subject line
            body: Email body text

        Returns:
            Dict with email metadata and sent status
        """
        email_record = {
            "to": to,
            "subject": subject,
            "body": body,
            "timestamp": datetime.now().isoformat(),
            "sent": True,
            "mock": True,
        }

        self.sent_emails.append(email_record)

        # Print to console for visibility during test
        print("\n" + "=" * 80)
        print("[EMAIL MOCK] Email would be sent")
        print("=" * 80)
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        print("=" * 80 + "\n")

        return email_record

    @staticmethod
    def send_email_static(to: str, subject: str, body: str) -> dict[str, Any]:
        """Static method for use as a tool (doesn't require instantiation)."""
        print("\n" + "=" * 80)
        print("[EMAIL MOCK] Email would be sent")
        print("=" * 80)
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        print("=" * 80 + "\n")

        return {
            "to": to,
            "subject": subject,
            "timestamp": datetime.now().isoformat(),
            "sent": True,
            "mock": True,
        }
