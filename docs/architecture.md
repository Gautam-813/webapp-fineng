# Architecture — TheFinanceCompany

## Overview
Single-server architecture where FastAPI serves both the frontend (HTML pages) and backend (JSON API).

```
User Browser
     |
     | HTTP requests
     v
FastAPI Server (single process)
     |
     |--- Jinja2 Templates --> HTML pages
     |--- JSON API Routes  --> Data endpoints
     |--- Static Files     --> CSS, JS, images
     |
     v
PostgreSQL Database
     |
     v
Payment Provider (Stripe/PayPal - future integration)
```

## Frontend
- **Rendering**: FastAPI renders HTML using Jinja2 templates
- **Styling**: Bootstrap 5 with custom CSS
- **Interactivity**: Vanilla JavaScript for cart, checkout, contact form
- **Static files**: Served by FastAPI via `StaticFiles` mount at `/static`

## Backend
- **Framework**: FastAPI (Python)
- **ORM**: SQLAlchemy
- **Templating**: Jinja2
- **Checkout**: Demo checkout creates confirmed orders without payment collection
- **Payment**: Stripe or PayPal SDK integration is reserved for a later production step

## Database
- **Engine**: PostgreSQL
- **Connection**: Async or sync via SQLAlchemy
- **Migrations**: Alembic (optional, for schema versioning)

## Request Flow (Example: Purchase)

1. User browses `/products` — FastAPI renders `products.html` with product data
2. User adds item to cart — JavaScript updates `localStorage`
3. User goes to `/checkout` — JavaScript reads cart from `localStorage`, calls `POST /api/checkout`
4. FastAPI validates product IDs/prices from the database and creates a confirmed demo order
5. FastAPI returns `/order/confirmation?order_id=...`
6. JavaScript clears the browser cart and redirects to the confirmation page
7. Admin order screens show the order as `confirmed`
8. Revenue still counts only `paid` orders, so demo confirmations do not create fake revenue
9. Future payment integration will add hosted payment sessions and validated webhooks

## Directory Structure
```
thefinanceengine/
  app/
    main.py              # FastAPI app entry point
    database.py          # DB connection setup
    models.py            # SQLAlchemy models
    schemas.py           # Pydantic schemas
    dependencies.py      # Shared dependencies
    routers/
      pages.py           # Page routes (GET /, /products, etc.)
      products.py        # Product API
      cart.py            # Cart API
      checkout.py        # Checkout API
      payments.py        # Payment webhook & redirects
      contact.py         # Contact & project request API
      admin.py           # Admin management routes
    templates/           # Jinja2 HTML templates
      base.html
      home.html
      products.html
      product_detail.html
      cart.html
      checkout.html
      about.html
      contact.html
      payment_success.html
      payment_cancelled.html
      partials/          # Reusable template fragments
        navbar.html
        footer.html
        product_card.html
        alert.html
        disclaimer.html
    static/
      css/
        styles.css
      js/
        cart.js
        checkout.js
        contact.js
      img/
        logo.png
        product-placeholders/
```
