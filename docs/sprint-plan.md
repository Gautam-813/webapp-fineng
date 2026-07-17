# Sprint Plan — TheFinanceCompany

## Sprint 1: Foundation
**Goal:** Set up project skeleton, database, and static pages.

- Initialize FastAPI project structure
- Set up PostgreSQL connection and SQLAlchemy models
- Create Jinja2 base template with Bootstrap
- Apply Bootstrap theme (navy + teal palette)
- Build static pages:
  - Home page (hero, featured products, CTAs)
  - About Us page
  - Contact Us page (static, no backend yet)
- Configure static file serving (CSS, JS, images)
- Implement product_categories and products models
- Seed initial product/category data

**Deliverables:**
- Running FastAPI app at localhost:8000
- Home, About, Contact pages render with proper theme
- Database tables created
- Product seed data loaded

---

## Sprint 2: Product Catalog
**Goal:** Display product catalog with filtering and detail pages.

- Build `/products` page with product cards grid
- Build `/products/{slug}` product detail page
- Implement product API endpoints:
  - `GET /api/products` (with category filter, search, sort)
  - `GET /api/products/{slug}`
  - `GET /api/categories`
- Add category filter sidebar
- Add search bar
- Add sorting dropdown (price, newest, name)
- Product card component (reusable partial)
- Risk disclaimer component

**Deliverables:**
- Products page with working filters, search, sort
- Product detail page with full info
- API endpoints returning JSON

---

## Sprint 3: Cart and Checkout
**Goal:** Add shopping cart and checkout flow.

- Build cart UI page (`/cart`)
- Implement cart with localStorage:
  - Add to cart button on product cards and detail pages
  - Cart icon with item count badge in navbar
  - Cart page with item list, totals, remove button
- Build checkout page (`/checkout`)
- Implement checkout form (name, email)
- Create checkout API endpoint (`POST /api/checkout`):
  - Validate cart items against database prices
  - Create pending order in PostgreSQL
  - Return order ID and payment redirect URL
- Implement order and order_item models

**Deliverables:**
- Working cart (add/remove/view)
- Checkout page with form
- Order creation on the backend
- Price validation (no client-side trust)

---

## Sprint 4: Payments
**Goal:** Integrate payment provider and complete purchase flow.

- Integrate Stripe or PayPal SDK
- Create payment session from checkout endpoint
- Add webhook endpoint (`POST /api/payments/webhook`)
- Handle payment success/cancelled redirects
- Mark orders as paid on webhook confirmation
- Create payment records in database
- Build success and cancelled pages
- Implement license key generation (if applicable)
- Send order confirmation (optional email)

**Deliverables:**
- End-to-end purchase flow
- Orders marked paid only via webhook (not browser redirect)
- Success/cancelled pages
- Payment records stored

---

## Sprint 5: Polish and Admin Basics
**Goal:** Admin management, contact handling, and final polish.

- Admin product management:
  - CRUD API for products
  - Basic admin page (or API-only v1)
  - Product status management (active/inactive/draft)
- Contact inquiry management:
  - View inquiries in admin
  - Update inquiry status
- Implement contact form backend:
  - `POST /api/contact`
  - `POST /api/custom-project-request`
- Add email notifications for inquiries and orders
- SEO metadata per page
- Custom error pages (404, 500)
- Security review:
  - Input validation
  - SQL injection prevention (via ORM)
  - CORS settings
  - Rate limiting considerations
- Final responsive testing

**Deliverables:**
- Admin can manage products
- Contact forms store inquiries
- Error pages styled
- SEO meta tags in templates
- Security review completed

---

## Future Sprints (Post v1)

| Sprint | Focus |
|--------|-------|
| 6 | User authentication (register/login/logout) |
| 7 | Customer dashboard (order history, downloads) |
| 8 | Licensing portal (activate, revoke, check licenses) |
| 9 | Analytics dashboard (sales, inquiries) |
| 10 | Multi-language support |
