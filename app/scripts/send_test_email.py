import argparse
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import get_settings
from app.email_service import EmailDeliveryError, send_otp_email


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a real OTP test email through the configured provider.")
    parser.add_argument("email", help="Recipient email address")
    parser.add_argument(
        "--purpose",
        choices=["registration", "password_reset"],
        default="registration",
        help="Template purpose to test",
    )
    parser.add_argument(
        "--code",
        default="",
        help="Optional fixed 6-digit code. If omitted, a random test code is generated.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not settings.email_enabled:
        print("Email is disabled. Set EMAIL_ENABLED=true in .env before sending a live test.")
        return 1

    code = args.code.strip() or f"{secrets.randbelow(1_000_000):06d}"
    if len(code) != 6 or not code.isdigit():
        print("--code must be exactly 6 digits")
        return 1

    try:
        message_id = send_otp_email(args.email, code, args.purpose)
    except EmailDeliveryError as exc:
        print(f"Email test failed: {exc}")
        return 1

    print(f"Email test sent to {args.email}")
    print(f"Purpose: {args.purpose}")
    print(f"Provider message id: {message_id or 'not returned'}")
    print("Check Inbox, Spam, Promotions, and Updates folders.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
