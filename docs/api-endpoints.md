# API Endpoints — TheFinanceCompany

## Page Routes (Jinja2 HTML responses)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home page |
| GET | `/products` | All products page |
| GET | `/products/{slug}` | Product detail page |
| GET | `/cart` | Shopping cart page |
| GET | `/checkout` | Checkout page |
| GET | `/about` | About Us page |
| GET | `/contact` | Contact Us page |
| GET | `/payment/success` | Payment success confirmation |
| GET | `/payment/cancelled` | Payment cancelled page |

## Product API

### GET /api/products
List all active products.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| category | str | Filter by category slug |
| search | str | Search by name |
| sort | str | `price_asc`, `price_desc`, `newest`, `name` |
| featured | bool | Filter featured products only |

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Gold Scalper EA",
    "slug": "gold-scalper-ea",
    "short_description": "...",
    "price": 149.00,
    "currency": "USD",
    "category": "Scalping",
    "platform": "MT4, MT5",
    "version": "2.1",
    "thumbnail_url": "/static/img/products/gold-scalper.png",
    "featured": true
  }
]
```

### GET /api/products/{slug}
Get a single product by slug.

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "Gold Scalper EA",
  "slug": "gold-scalper-ea",
  "description": "Full HTML description",
  "price": 149.00,
  "currency": "USD",
  "category": "Scalping",
  "platform": "MT4, MT5",
  "version": "2.1",
  "images": [...],
  "download_url": null,
  "created_at": "2026-01-01T00:00:00Z"
}
```

**Error:** `404 Not Found`

### GET /api/categories
List all product categories.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Scalping",
    "slug": "scalping",
    "description": "...",
    "product_count": 5
  }
]
```

## Cart API (optional backend storage)

### GET /api/cart
Get current cart contents.

**Response:** `200 OK`
```json
{
  "cart_id": 1,
  "items": [
    {
      "item_id": 1,
      "product_id": 1,
      "name": "Gold Scalper EA",
      "unit_price": 149.00,
      "quantity": 1,
      "total": 149.00
    }
  ],
  "subtotal": 149.00
}
```

### POST /api/cart/items
Add item to cart.

**Request:**
```json
{
  "product_id": 1,
  "quantity": 1
}
```

**Response:** `201 Created`

### PUT /api/cart/items/{item_id}
Update item quantity.

**Request:**
```json
{
  "quantity": 2
}
```

**Response:** `200 OK`

### DELETE /api/cart/items/{item_id}
Remove item from cart.

**Response:** `204 No Content`

### DELETE /api/cart
Clear entire cart.

**Response:** `204 No Content`

## Checkout API

### POST /api/checkout
Create order and initiate payment session.

**Request:**
```json
{
  "customer_name": "John Smith",
  "customer_email": "john@example.com",
  "items": [
    {
      "product_id": 1,
      "quantity": 1
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "order_id": 123,
  "payment_url": "https://checkout.stripe.com/pay/cs_test_..."
}
```

**Error:** `400 Bad Request` — Invalid items, missing fields
**Error:** `422 Unprocessable Entity` — Validation error

## Payment API

### POST /api/payments/webhook
Webhook endpoint for payment provider callbacks.

**Request:** Provider-specific payload (Stripe event / PayPal webhook)

**Response:** `200 OK`
```json
{
  "status": "received"
}
```

## Contact API

### POST /api/contact
Submit a contact inquiry.

**Request:**
```json
{
  "name": "John Smith",
  "email": "john@example.com",
  "phone": "+1234567890",
  "company": "Trade Corp",
  "subject": "Product question",
  "message": "I have a question about Gold Scalper EA.",
  "service_type": "product_support"
}
```

**Response:** `201 Created`
```json
{
  "message": "Inquiry received. We will get back to you shortly."
}
```

### POST /api/custom-project-request
Submit a custom development project request.

**Request:**
```json
{
  "name": "John Smith",
  "email": "john@example.com",
  "phone": "+1234567890",
  "company": "Trade Corp",
  "project_type": "Custom EA",
  "budget_range": "$5,000 - $10,000",
  "timeline": "3 months",
  "description": "I need a custom EA that..."
}
```

**Response:** `201 Created`
```json
{
  "message": "Project request submitted. We will review and contact you."
}
```

## Admin API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/products` | List all products (incl. inactive) |
| POST | `/api/admin/products` | Create product |
| PUT | `/api/admin/products/{id}` | Update product |
| DELETE | `/api/admin/products/{id}` | Delete product |
| GET | `/api/admin/orders` | List all orders |
| PUT | `/api/admin/orders/{id}/status` | Update order status |
| GET | `/api/admin/inquiries` | List contact inquiries |
| PUT | `/api/admin/inquiries/{id}/status` | Update inquiry status |

## Authentication API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create/update a pending customer registration and send OTP |
| POST | `/api/auth/register/verify` | Verify registration OTP and activate account |
| POST | `/api/auth/otp/resend` | Resend registration or password reset OTP |
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Get current authenticated user |
| POST | `/api/auth/forgot-password` | Send password reset OTP if account exists |
| POST | `/api/auth/reset-password` | Verify reset OTP and set a new password |
| GET | `/api/account/profile` | Get customer profile |
| PUT | `/api/account/profile` | Update customer profile |
| GET | `/api/account/orders` | Get user's order history |
| GET | `/api/account/projects` | Get user's custom project requests |
| GET | `/api/account/support` | Get user's support inquiries |

Registration now creates customer users with `pending_verification` status. Login is blocked until `/api/auth/register/verify` successfully verifies the emailed OTP. OTPs are stored hashed, expire after the configured window, and are consumed after successful verification.
