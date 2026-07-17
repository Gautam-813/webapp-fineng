# Database Schema — TheFinanceCompany

## Tables Overview

### users
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| email | VARCHAR(255) UNIQUE NOT NULL | |
| password_hash | VARCHAR(255) | Nullable for guest checkout |
| full_name | VARCHAR(255) | |
| phone | VARCHAR(50) | |
| role | VARCHAR(20) DEFAULT 'customer' | customer / admin |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

### product_categories
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| name | VARCHAR(255) NOT NULL | |
| slug | VARCHAR(255) UNIQUE NOT NULL | |
| description | TEXT | |
| created_at | TIMESTAMP DEFAULT NOW() | |

### products
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| name | VARCHAR(255) NOT NULL | |
| slug | VARCHAR(255) UNIQUE NOT NULL | |
| short_description | VARCHAR(500) | |
| description | TEXT | |
| price | DECIMAL(10,2) NOT NULL | |
| currency | VARCHAR(3) DEFAULT 'USD' | |
| category_id | INT FK -> product_categories.id | |
| status | VARCHAR(20) DEFAULT 'active' | active / inactive / draft |
| version | VARCHAR(50) | |
| platform | VARCHAR(50) | MT4 / MT5 / Web / Desktop |
| download_url | VARCHAR(500) | |
| thumbnail_url | VARCHAR(500) | |
| featured | BOOLEAN DEFAULT FALSE | |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

Index: `idx_products_status` on `status`
Index: `idx_products_category` on `category_id`
Index: `idx_products_slug` on `slug`

### product_images
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| product_id | INT FK -> products.id ON DELETE CASCADE | |
| image_url | VARCHAR(500) NOT NULL | |
| alt_text | VARCHAR(255) | |
| sort_order | INT DEFAULT 0 | |
| created_at | TIMESTAMP DEFAULT NOW() | |

### carts
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| user_id | INT FK -> users.id | Nullable |
| session_id | VARCHAR(255) | For guest carts |
| status | VARCHAR(20) DEFAULT 'active' | active / converted / abandoned |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

### cart_items
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| cart_id | INT FK -> carts.id ON DELETE CASCADE | |
| product_id | INT FK -> products.id | |
| quantity | INT DEFAULT 1 | |
| unit_price | DECIMAL(10,2) NOT NULL | Snapshot of price at add time |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

### orders
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| user_id | INT FK -> users.id | Nullable |
| customer_email | VARCHAR(255) NOT NULL | |
| customer_name | VARCHAR(255) NOT NULL | |
| status | VARCHAR(20) DEFAULT 'pending' | pending / paid / failed / refunded / cancelled |
| subtotal | DECIMAL(10,2) | |
| tax_amount | DECIMAL(10,2) DEFAULT 0 | |
| discount_amount | DECIMAL(10,2) DEFAULT 0 | |
| total_amount | DECIMAL(10,2) NOT NULL | |
| currency | VARCHAR(3) DEFAULT 'USD' | |
| payment_provider | VARCHAR(50) | stripe / paypal |
| payment_reference | VARCHAR(255) | |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

Index: `idx_orders_status` on `status`
Index: `idx_orders_email` on `customer_email`

### order_items
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| order_id | INT FK -> orders.id ON DELETE CASCADE | |
| product_id | INT FK -> products.id | |
| product_name | VARCHAR(255) | Snapshot at order time |
| quantity | INT DEFAULT 1 | |
| unit_price | DECIMAL(10,2) | |
| total_price | DECIMAL(10,2) | |
| created_at | TIMESTAMP DEFAULT NOW() | |

### payments
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| order_id | INT FK -> orders.id | |
| provider | VARCHAR(50) NOT NULL | stripe / paypal |
| provider_payment_id | VARCHAR(255) | |
| status | VARCHAR(20) DEFAULT 'pending' | pending / succeeded / failed / refunded |
| amount | DECIMAL(10,2) | |
| currency | VARCHAR(3) | |
| raw_response_json | JSONB | Full provider response |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

### licenses
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| order_id | INT FK -> orders.id | |
| product_id | INT FK -> products.id | |
| user_id | INT FK -> users.id | Nullable |
| license_key | VARCHAR(255) UNIQUE NOT NULL | |
| status | VARCHAR(20) DEFAULT 'active' | active / revoked / expired |
| expires_at | TIMESTAMP | Nullable |
| created_at | TIMESTAMP DEFAULT NOW() | |

### contact_inquiries
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| name | VARCHAR(255) NOT NULL | |
| email | VARCHAR(255) NOT NULL | |
| phone | VARCHAR(50) | |
| company | VARCHAR(255) | |
| subject | VARCHAR(255) | |
| message | TEXT NOT NULL | |
| service_type | VARCHAR(50) DEFAULT 'general' | product_support / custom_development / general |
| status | VARCHAR(20) DEFAULT 'new' | new / in_progress / resolved |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

### custom_project_requests
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| name | VARCHAR(255) NOT NULL | |
| email | VARCHAR(255) NOT NULL | |
| phone | VARCHAR(50) | |
| company | VARCHAR(255) | |
| project_type | VARCHAR(255) | |
| budget_range | VARCHAR(100) | |
| timeline | VARCHAR(255) | |
| description | TEXT NOT NULL | |
| status | VARCHAR(20) DEFAULT 'new' | new / reviewing / contacted / closed |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

## Entity Relationships
```
product_categories 1---* products
products 1---* product_images
products 1---* cart_items
carts 1---* cart_items
users 1---* carts
users 1---* orders
orders 1---* order_items
orders 1---* payments
orders 1---* licenses
products 1---* licenses
```
