# TheFinanceCompany Web App

FastAPI and Jinja2 web app for TheFinanceCompany, a fintech software business selling pre-built trading tools and collecting custom algo-trading project requests.

## Current State

- Public pages: home, products, product detail, cart, checkout, about, contact, legal pages.
- Product catalog: filtering, search, sorting, pagination, product detail pages, thumbnails, and gallery images.
- Demo checkout: creates real database orders with status `confirmed`; no payment is collected yet.
- Customer portal: dashboard, order history, profile, support history, and custom project request history.
- Admin panel: products, categories, customers, orders, inquiries, and project requests.
- Authentication: email/password login, Gmail-only customer registration, emailed OTP verification, forgot password OTP reset, role-based admin access.
- Security controls: security headers, rate limiting, trusted hosts, secure-cookie settings, and same-origin CSRF protection for state-changing browser requests.

## Local Development

```bash
pip install -r requirements.txt
python app/scripts/seed_data.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

## Environment

Copy `.env.example` to `.env` and adjust values for your local or production setup. Important production values include:

```env
ENVIRONMENT=production
DEBUG=false
AUTO_CREATE_TABLES=false
SECRET_KEY=replace-with-at-least-32-random-characters
SECURE_COOKIES=true
ALLOWED_HOSTS=thefinancecompany.com,www.thefinancecompany.com
CORS_ORIGINS=https://thefinancecompany.com,https://www.thefinancecompany.com
CSRF_PROTECTION_ENABLED=true
CSRF_EXEMPT_PATHS=/api/payments/webhook
EMAIL_ENABLED=true
RESEND_API_KEY=...
EMAIL_FROM_LOGIN=login@thefinanceengine.com
REGISTRATION_ALLOWED_DOMAINS=gmail.com
SITE_URL=https://thefinancecompany.com
```

## Verification

```bash
python -m compileall app -q
python app/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

The smoke test checks public pages, catalog/detail pages, cart behavior, demo checkout, customer portal, admin pages/APIs, and CSRF origin protection.

To send a live OTP email test after `.env` is configured:

```bash
python app/scripts/send_test_email.py user@gmail.com --purpose registration
python app/scripts/send_test_email.py user@gmail.com --purpose password_reset
```

## Documentation

- `docs/architecture.md` - current technical architecture and request flow.
- `docs/api-endpoints.md` - current page and API route reference.
- `docs/database-schema.md` - database table reference.
- `docs/database-migrations.md` - migration workflow.
- `docs/production-readiness.md` - launch checklist and known gaps.
- `docs/visual-qa-checklist.md` - frontend QA checklist.

## Known Pending Work

- Real payment provider integration and verified payment webhooks.
- Licensing/download delivery integration from the licensing workstream.
- Production hosting, database backups, monitoring, and deployment runbook.
- Final legal/business policy review.
