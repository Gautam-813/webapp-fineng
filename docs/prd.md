# Product Requirements Document — TheFinanceCompany

## 1. Product Goal
A website that sells pre-built financial software (Expert Advisors / EAs) and generates leads for custom software development services.

## 2. Target Audience
- Forex/trading individuals and firms looking for ready-made EAs
- Businesses needing bespoke financial software development

## 3. Core Objectives
1. Present the company as trustworthy and technically capable
2. Sell pre-built EA products with a smooth purchase flow
3. Generate qualified leads for custom development projects

## 4. User Stories

### Browse Products
- As a visitor, I can view all available EAs with prices and descriptions
- As a visitor, I can filter products by category and sort by price/name
- As a visitor, I can search products by name
- As a visitor, I can view detailed information about a specific EA

### Purchase Products
- As a customer, I can add EAs to my shopping cart
- As a customer, I can review my cart before checkout
- As a customer, I can check out with my name and email
- As a customer, I can place a demo order without payment while payment integration is pending
- As a customer, I receive an order confirmation after checkout

### Contact & Inquiries
- As a visitor, I can contact the company via a contact form
- As a visitor, I can submit a custom software development request

### Company Information
- As a visitor, I can learn about the company's background and expertise
- As a visitor, I can understand the risks involved with trading EAs

## 5. Functional Requirements

| ID | Feature | Description |
|----|---------|-------------|
| F1 | Product Catalog | Display all EAs with thumbnails, prices, categories |
| F2 | Product Detail | Full description, features, platform compatibility, price |
| F3 | Shopping Cart | Add/remove items, view totals, stored in localStorage |
| F4 | Checkout | Collect customer info, validate prices server-side, create confirmed demo order |
| F5 | Payment Integration | Future hosted payment page, webhook confirmation, refunds, and paid status transitions |
| F6 | Contact Form | Name, email, phone, company, subject, message |
| F7 | Custom Project Request | Project type, budget, timeline, description |
| F8 | About Page | Static company information |

## 6. Non-Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| N1 | Performance | Pages load within 2 seconds |
| N2 | Security | No pricing from frontend; backend validates all prices |
| N3 | Maintainability | Simple stack, well-structured code, minimal dependencies |
| N4 | Mobile Responsive | Bootstrap-based, works on all screen sizes |
| N5 | SEO | Clean URLs, meta tags, semantic HTML |

## 7. Constraints
- Frontend: HTML, CSS, JavaScript, Bootstrap only (no SPA framework)
- Backend: FastAPI (Python)
- Database: PostgreSQL
- Single server deployment (FastAPI serves both frontend and API)
