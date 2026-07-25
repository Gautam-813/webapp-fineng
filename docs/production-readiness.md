# Production Readiness Checklist

This project is currently a functional demo web app for TheFinanceCompany. The buyer flow, product catalog, product detail pages, customer accounts, demo checkout, and admin management screens are in place, but a few production controls must be finished before real customers and money are involved.

## Current Demo State

- Checkout creates real database orders with status `confirmed`.
- Demo checkout does not collect payment and does not count confirmed orders as paid revenue.
- Products, categories, orders, inquiries, project requests, and users are manageable from admin screens.
- Product thumbnail and gallery image uploads are supported for product detail pages.
- Customer registration and login use email/password only. There is no OTP or email verification yet.
- Downloads and licensing are intentionally left for the licensing system integration.

## Must Finish Before Production

- Replace the default `SECRET_KEY` and all demo credentials with environment-managed production secrets.
- Use a production database such as PostgreSQL with backups, restore testing, and restricted database credentials.
- Keep schema changes in Alembic migrations and run them before each production deployment.
- Enable HTTPS at the deployment edge and use `SECURE_COOKIES=true` in production.
- Keep app rate limiting enabled for login, registration, checkout, contact, and project request endpoints; add proxy/WAF-level limits before launch.
- Add CSRF protection or a clear same-site API strategy for browser form actions.
- Add email verification or OTP if the business requires verified Gmail-only registration later.
- Add password reset, account recovery, and admin password rotation procedures.
- Add real payment integration, webhook validation, payment status transitions, and refund handling.
- Integrate the licensing/download system after payment or confirmed manual approval rules are decided.
- Keep upload size limits enabled and add production object storage for product media.
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
MAX_UPLOAD_SIZE_MB=5
```

The app also adds baseline security headers, including clickjacking protection, content-type sniffing protection, referrer policy, permissions policy, and a conservative content security policy compatible with the current Bootstrap CDN setup.

## Known Demo Constraints

- `confirmed` means the customer placed an order, not that money was collected.
- Admin revenue intentionally counts only `paid` orders.
- Product download files are not delivered by this app yet.
- Licensing will be connected later by the licensing-system workstream.
- Gmail-only registration and authentic Gmail verification are not enforced yet.
