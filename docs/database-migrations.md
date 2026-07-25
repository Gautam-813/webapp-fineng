# Database Migrations

TheFinanceCompany uses Alembic for production database schema changes.

## Local Development

Local SQLite development can auto-create tables for convenience:

```env
DATABASE_URL=sqlite:///./thefinancecompany.db
AUTO_CREATE_TABLES=true
```

This keeps demos easy to run. It is not the production workflow.

## Production Workflow

Production should use PostgreSQL and explicit migrations:

```env
DATABASE_URL=postgresql://user:password@host:5432/thefinancecompany
ENVIRONMENT=production
AUTO_CREATE_TABLES=false
SECRET_KEY=replace-with-a-real-secret
DEBUG=false
SECURE_COOKIES=true
ALLOWED_HOSTS=thefinancecompany.com,www.thefinancecompany.com
```

Before starting or restarting the app in production, run:

```bash
alembic upgrade head
```

Then start the application:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Creating Future Migrations

After changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe change"
```

Review the generated migration carefully before committing it. Confirm indexes, nullability, defaults, and destructive changes are intentional.

Apply locally against a disposable database first:

```bash
alembic upgrade head
```

## Existing SQLite Demo Databases

Do not run the initial migration against an existing SQLite database that was already created with `Base.metadata.create_all()`, because the tables already exist. Existing local demo databases can continue to run with `AUTO_CREATE_TABLES=true`.

For a clean migration test, point `DATABASE_URL` at a new empty SQLite file or a new PostgreSQL database, then run `alembic upgrade head`.

## Deployment Checklist

- Back up the database before migrations.
- Review the migration file before applying.
- Run `alembic upgrade head`.
- Start the app with `AUTO_CREATE_TABLES=false`.
- Run the smoke test against the deployed URL.
- Confirm admin dashboard, product catalog, checkout, account orders, and contact/project requests work.
