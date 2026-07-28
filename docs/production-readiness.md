# Production Readiness Checklist

This project is currently a functional demo web app for TheFinanceCompany. The buyer flow, product catalog, product detail pages, customer accounts, demo checkout, and admin management screens are in place, but a few production controls must be finished before real customers and money are involved.

## Current Demo State

- Checkout creates real database orders with status `confirmed`.
- Demo checkout does not collect payment and does not count confirmed orders as paid revenue.
- Products, categories, orders, inquiries, project requests, and users are manageable from admin screens.
- Product thumbnail and gallery image uploads are supported for product detail pages.
- Customer registration uses Gmail-only email addresses and emailed OTP verification through Resend.
- Forgot password uses emailed OTP verification before changing the password.
- Cookie-authenticated state-changing requests are protected by same-origin CSRF checks.
- EA licensing supports admin-issued keys, customer MT account binding, and versioned validation API checks.
- Product downloads are delivered through license-gated account endpoints; software-device licensing remains a later step.

## Must Finish Before Production

- Replace the default `SECRET_KEY` and all demo credentials with environment-managed production secrets.
- Use a production database such as PostgreSQL with backups, restore testing, and restricted database credentials.
- Keep schema changes in Alembic migrations and run them before each production deployment.
- Enable HTTPS at the deployment edge and use `SECURE_COOKIES=true` in production.
- Keep app rate limiting enabled for login, registration, checkout, contact, and project request endpoints; add proxy/WAF-level limits before launch.
- Keep CSRF protection enabled and configure `SITE_URL`, `CORS_ORIGINS`, and `CSRF_EXEMPT_PATHS` for the production domain and payment webhooks.
- Monitor OTP delivery, bounce/spam placement, resend rates, provider message IDs, and failed verification attempts.
- Add admin password rotation procedures.
- Add real payment integration, webhook validation, payment status transitions, and refund handling.
- Connect automatic license issuance to paid orders or confirmed manual approval rules.
- Complete software-device fingerprint licensing after EA license validation is stable.
- Keep upload size limits enabled and add production object storage for product media and protected product files.
- Add audit logging for admin edits to products, users, order statuses, and categories.
- Add transactional email notifications for order confirmation, contact receipt, and admin alerts.
- Add legal pages: terms, privacy policy, refund policy, risk disclaimer, and support policy.
- Add monitoring for application errors, slow endpoints, failed logins, failed checkouts, and payment webhooks.
- Add a deployment runbook covering environment variables, database migration, seed/admin setup, smoke tests, rollback, and backups.

## Smoke Test

Use the smoke test before demos, after deployments, and after changes to the buyer or admin flows.

1. Start the app:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. Seed demo data if needed:

```bash
python app/scripts/seed_data.py
```

3. Run the smoke test:

```bash
python app/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

Useful options:

```bash
python app/scripts/smoke_test.py --skip-admin
python app/scripts/smoke_test.py --keep-data
python app/scripts/smoke_test.py --admin-email admin@thefinancecompany.com --admin-password admin123
```

The script checks public pages, catalog pagination, product detail rendering, cart actions, empty checkout validation, customer registration/login, demo order creation, customer account history, admin pages, admin paginated APIs, and admin order search. Temporary customer, cart, and order data is cleaned up automatically unless `--keep-data` is passed.

## Email Delivery Check

Use the manual email test before production deploys, DNS changes, sender changes, or OTP template edits:

```bash
python app/scripts/send_test_email.py test-recipient@gmail.com --purpose registration
python app/scripts/send_test_email.py test-recipient@gmail.com --purpose password_reset
```

The script uses the real Resend API and prints the provider message ID. Check Inbox, Spam, Promotions, and Updates folders for the test email. The app logs email send attempts, failures, and provider IDs without logging OTP values or API keys.

## Visual QA

Use `docs/visual-qa-checklist.md` after frontend changes. The current visual QA pass checks public, buyer, account, legal, and admin pages at desktop and mobile widths for horizontal overflow, clipped controls, broken images, and console errors.

## Database Deployment

Production should run with `AUTO_CREATE_TABLES=false`. Apply schema changes explicitly with:

```bash
alembic upgrade head
```

Local SQLite auto-create remains available for quick demos and development only.

## Production Security Settings

Production startup is intentionally strict when `ENVIRONMENT=production`. Required settings:

```env
ENVIRONMENT=production
DEBUG=false
AUTO_CREATE_TABLES=false
SECRET_KEY=replace-with-at-least-32-random-characters
SECURE_COOKIES=true
ALLOWED_HOSTS=thefinancecompany.com,www.thefinancecompany.com
CORS_ORIGINS=https://thefinancecompany.com,https://www.thefinancecompany.com
RATE_LIMIT_ENABLED=true
CSRF_PROTECTION_ENABLED=true
CSRF_EXEMPT_PATHS=/api/payments/webhook
MAX_UPLOAD_SIZE_MB=5
EMAIL_ENABLED=true
RESEND_API_KEY=...
EMAIL_FROM_LOGIN=login@thefinanceengine.com
OTP_EXPIRY_MINUTES=10
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_ATTEMPTS=5
REGISTRATION_ALLOWED_DOMAINS=gmail.com
SITE_URL=https://thefinancecompany.com
```

The app also adds baseline security headers, including clickjacking protection, content-type sniffing protection, referrer policy, permissions policy, and a conservative content security policy compatible with the current Bootstrap CDN setup. State-changing browser requests are checked against the request origin/referer so authenticated cookie requests cannot be triggered from another site.

## Known Demo Constraints

- `confirmed` means the customer placed an order, not that money was collected.
- Admin revenue intentionally counts only `paid` orders.
- Automatic license issuance after payment is not connected yet.
- Software-device fingerprint licensing will be connected later by the licensing-system workstream.
- Google OAuth/Gmail login is not implemented yet; registration currently uses email/password plus OTP.
