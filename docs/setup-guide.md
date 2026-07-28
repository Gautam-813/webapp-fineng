# Setup Guide — TheFinanceCompany

## Prerequisites
- Python 3.10 or higher
- PostgreSQL 14 or higher
- Git
- Resend account and verified sending domain for OTP email delivery
- Stripe / PayPal account only when production payment collection is added later

## Local Development Setup

### 1. Clone the Repository
```bash
git clone <repo-url>
cd thefinanceengine
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate    # Linux/Mac
venv\Scripts\activate       # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/thefinancecompany
ENVIRONMENT=production
DEBUG=false
AUTO_CREATE_TABLES=false
SECRET_KEY=your-secret-key-here
SECURE_COOKIES=true
ALLOWED_HOSTS=thefinancecompany.com,www.thefinancecompany.com
CORS_ORIGINS=https://thefinancecompany.com,https://www.thefinancecompany.com
CSRF_PROTECTION_ENABLED=true
CSRF_EXEMPT_PATHS=/api/payments/webhook
RATE_LIMIT_ENABLED=true
MAX_UPLOAD_SIZE_MB=5

EMAIL_ENABLED=true
RESEND_API_KEY=re_...
EMAIL_FROM_LOGIN=login@thefinanceengine.com
OTP_EXPIRY_MINUTES=10
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_ATTEMPTS=5
REGISTRATION_ALLOWED_DOMAINS=gmail.com
SITE_URL=https://thefinancecompany.com

STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_MODE=sandbox
```

### 5. Set Up PostgreSQL
```sql
CREATE DATABASE thefinancecompany;
```

### 6. Run Database Migrations
```bash
alembic upgrade head
```

Local SQLite development can use `AUTO_CREATE_TABLES=true` to auto-create tables on app startup. Production should use `AUTO_CREATE_TABLES=false` and run Alembic migrations explicitly before the app starts.

### 7. Seed Sample Data (Optional)
```bash
python app/scripts/seed_data.py
```

### 8. Run the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

### 9. Open the Website
Visit `http://localhost:8000`

Customer registration requires a Gmail address and a valid OTP sent through Resend when `EMAIL_ENABLED=true`.

### 10. Send a Test OTP Email
```bash
python app/scripts/send_test_email.py your-test@gmail.com --purpose registration
python app/scripts/send_test_email.py your-test@gmail.com --purpose password_reset
```

The script prints the Resend message ID when delivery is accepted. Check Inbox, Spam, Promotions, and Updates folders.

## Project Dependencies (`requirements.txt`)
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
psycopg2-binary==2.9.9
alembic==1.13.0
jinja2==3.1.4
python-multipart==0.0.9
stripe==9.0.0
python-dotenv==1.0.1
pydantic==2.8.0
pydantic-settings==2.3.0
```

## Running Tests
```bash
python app/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

## Deployment

### Docker (Recommended)
```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t thefinancecompany .
docker run -p 8000:8000 --env-file .env thefinancecompany
```

### Traditional VPS
1. Install Python, PostgreSQL, and a reverse proxy (nginx/caddy)
2. Clone the project
3. Set up environment variables
4. Run with a process manager (systemd, supervisor)
5. Configure nginx to proxy to localhost:8000
6. Set up SSL with Let's Encrypt
