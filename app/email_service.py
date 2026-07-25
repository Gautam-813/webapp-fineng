import requests
from app.config import get_settings


class EmailDeliveryError(RuntimeError):
    pass


def send_transactional_email(to_email: str, subject: str, html: str, text: str | None = None) -> str | None:
    settings = get_settings()
    if not settings.email_enabled:
        return None
    if not settings.resend_api_key:
        raise EmailDeliveryError("Email is enabled but RESEND_API_KEY is missing")

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": settings.email_from_login,
            "to": [to_email],
            "subject": subject,
            "html": html,
            "text": text or _plain_text_from_html(html),
        },
        timeout=20,
    )
    if response.status_code >= 400:
        try:
            detail = response.json().get("message") or response.text
        except ValueError:
            detail = response.text
        raise EmailDeliveryError(f"Email delivery failed: {detail}")

    try:
        return response.json().get("id")
    except ValueError:
        return None


def send_otp_email(to_email: str, otp_code: str, purpose: str) -> str | None:
    purpose_label = "password reset" if purpose == "password_reset" else "account verification"
    subject = "Your TheFinanceEngine verification code"
    html = f"""
    <div style="font-family:Arial,sans-serif;line-height:1.55;color:#0b1f33;max-width:560px">
      <h2 style="margin:0 0 12px">TheFinanceEngine verification code</h2>
      <p>Use this one-time code for {purpose_label}:</p>
      <div style="font-size:30px;font-weight:700;letter-spacing:6px;background:#f3f7f9;border:1px solid #d9e5ea;border-radius:8px;padding:16px 20px;text-align:center;margin:18px 0">{otp_code}</div>
      <p>This code expires in 10 minutes. If you did not request this, you can ignore this email.</p>
      <p style="font-size:13px;color:#667085">TheFinanceEngine automated security email.</p>
    </div>
    """
    text = f"Your TheFinanceEngine verification code is {otp_code}. This code expires in 10 minutes."
    return send_transactional_email(to_email, subject, html, text)


def _plain_text_from_html(html: str) -> str:
    return " ".join(html.replace("<", " <").split())
