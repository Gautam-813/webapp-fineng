import html
import logging
import re

import requests
from app.config import get_settings


logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    pass


def send_transactional_email(
    to_email: str,
    subject: str,
    html_body: str,
    text: str | None = None,
    email_type: str = "transactional",
) -> str | None:
    settings = get_settings()
    recipient_domain = _email_domain(to_email)
    if not settings.email_enabled:
        logger.info("email_skipped disabled type=%s recipient_domain=%s", email_type, recipient_domain)
        return None
    if not settings.resend_api_key:
        logger.error("email_failed missing_resend_api_key type=%s recipient_domain=%s", email_type, recipient_domain)
        raise EmailDeliveryError("Email is enabled but RESEND_API_KEY is missing")

    logger.info("email_send_attempt type=%s recipient_domain=%s", email_type, recipient_domain)
    try:
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
                "html": html_body,
                "text": text or _plain_text_from_html(html_body),
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        logger.exception("email_failed request_error type=%s recipient_domain=%s", email_type, recipient_domain)
        raise EmailDeliveryError("Email delivery failed. Please try again shortly.") from exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("message") or response.text
        except ValueError:
            detail = response.text
        logger.error(
            "email_failed provider_error type=%s recipient_domain=%s status_code=%s detail=%s",
            email_type,
            recipient_domain,
            response.status_code,
            _safe_provider_detail(detail),
        )
        raise EmailDeliveryError("Email delivery failed. Please try again shortly.")

    try:
        message_id = response.json().get("id")
    except ValueError:
        message_id = None

    logger.info("email_sent type=%s recipient_domain=%s provider_id=%s", email_type, recipient_domain, message_id or "unknown")
    return message_id


def send_otp_email(to_email: str, otp_code: str, purpose: str) -> str | None:
    subject, html_body, text = _build_otp_email(otp_code, purpose)
    return send_transactional_email(to_email, subject, html_body, text, email_type=f"otp_{purpose}")


def _build_otp_email(otp_code: str, purpose: str) -> tuple[str, str, str]:
    settings = get_settings()
    if purpose == "password_reset":
        subject = "Reset your TheFinanceEngine password"
        heading = "Password reset code"
        intro = "Use this one-time code to reset your TheFinanceEngine password."
    else:
        subject = "Your TheFinanceEngine verification code"
        heading = "Verify your account"
        intro = "Use this one-time code to finish creating your TheFinanceEngine account."

    expiry_minutes = settings.otp_expiry_minutes
    safe_code = html.escape(otp_code)
    safe_intro = html.escape(intro)
    safe_heading = html.escape(heading)
    html_body = f"""
    <div style="margin:0;padding:0;background:#f4f7f9;font-family:Arial,Helvetica,sans-serif;color:#102033">
      <div style="max-width:600px;margin:0 auto;padding:32px 16px">
        <div style="background:#ffffff;border:1px solid #dce6ec;border-radius:12px;overflow:hidden">
          <div style="background:#0b1f33;padding:22px 26px;color:#ffffff">
            <div style="font-size:14px;letter-spacing:.02em;color:#9be7d8">TheFinanceEngine</div>
            <h1 style="font-size:24px;line-height:1.25;margin:8px 0 0">{safe_heading}</h1>
          </div>
          <div style="padding:26px">
            <p style="font-size:16px;line-height:1.6;margin:0 0 18px">{safe_intro}</p>
            <div style="font-size:34px;font-weight:700;letter-spacing:8px;background:#eef7f5;border:1px solid #b7ded5;border-radius:10px;padding:18px 20px;text-align:center;margin:22px 0;color:#0b1f33">{safe_code}</div>
            <p style="font-size:15px;line-height:1.6;margin:0 0 14px">This code expires in {expiry_minutes} minutes. For your security, do not share it with anyone.</p>
            <p style="font-size:14px;line-height:1.6;margin:0 0 18px;color:#536471">If you cannot find this email later, check your Spam, Promotions, or Updates folder.</p>
            <p style="font-size:14px;line-height:1.6;margin:0;color:#536471">If you did not request this code, you can safely ignore this email.</p>
          </div>
        </div>
        <p style="font-size:12px;line-height:1.5;color:#687782;margin:18px 6px 0">Automated security email from TheFinanceEngine. This inbox is not monitored for support requests.</p>
      </div>
    </div>
    """
    text = (
        f"{heading}\n\n"
        f"{intro}\n\n"
        f"Code: {otp_code}\n\n"
        f"This code expires in {expiry_minutes} minutes. Do not share it with anyone.\n\n"
        "If you cannot find this email later, check your Spam, Promotions, or Updates folder.\n"
        "If you did not request this code, you can safely ignore this email."
    )
    return subject, html_body, text


def _plain_text_from_html(html_body: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", html_body)
    return " ".join(html.unescape(without_tags).split())


def _email_domain(to_email: str) -> str:
    return to_email.rsplit("@", 1)[-1].lower() if "@" in to_email else "unknown"


def _safe_provider_detail(detail: str) -> str:
    return re.sub(r"[\w.+-]+@[\w.-]+", "[email]", detail)[:300]
