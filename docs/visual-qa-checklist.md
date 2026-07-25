# Visual QA Checklist

Use this checklist before demos, before production releases, and after frontend changes that touch layout, navigation, forms, cards, tables, or responsive behavior.

## Viewports

Check at minimum:

- Desktop: `1366 x 900`
- Mobile: `390 x 844`

Add tablet checks when a change heavily affects grids, admin tables, or product cards:

- Tablet: `768 x 1024`

## Public Pages

- `/`
- `/products`
- `/products/gold-scalper-pro` or another seeded product detail page
- `/cart`
- `/checkout`
- `/login`
- `/register`
- `/account`
- `/about`
- `/contact`
- `/risk-disclaimer`
- `/terms`
- `/privacy-policy`
- `/refund-policy`
- `/payment/success`
- `/order/confirmation?order_id=123`

## Admin Pages

Log in as the seeded admin account first:

- `/admin`
- `/admin/products`
- `/admin/products/new`
- `/admin/categories`
- `/admin/customers`
- `/admin/orders`
- `/admin/inquiries`

## Pass Criteria

Each page should pass:

- No horizontal page overflow at desktop or mobile widths.
- No button, tab, badge, input, or select text clipped inside its own box.
- No unreadable dark text on dark backgrounds or pale text on pale backgrounds.
- No incoherent overlap between headings, cards, controls, images, and tables.
- Mobile navbar opens cleanly and does not push content off screen.
- Product cards keep stable dimensions and actions fit on mobile.
- Product detail image/gallery area does not create horizontal scroll.
- Cart and checkout rows stack cleanly on mobile.
- Admin tables sit inside scrollable table containers when needed.
- Admin filters, search, and pagination controls wrap without overlap.
- Legal pages are readable and their sidebar stacks correctly on mobile.
- No broken images.
- No app console errors.

## Current Visual QA Run

Date: 2026-07-23

Checked:

- Public pages at `1366 x 900` and `390 x 844`
- Admin pages at `1366 x 900` and `390 x 844`
- Product detail, auth, account, and confirmation pages at both sizes

Findings fixed:

- Mobile `/about` had a 12px horizontal overflow from a large Bootstrap `g-5` hero gutter.
- Mobile product detail had the same 12px overflow from a large `g-5` hero gutter.

Fixes applied:

- Reduced the About hero row gutter on small screens.
- Reduced the product detail hero row gutter on small screens.
- Bumped the stylesheet cache key to `20260723-visual-qa`.

Current result:

- No horizontal overflow found in the checked public pages.
- No horizontal overflow found in the checked admin pages.
- No broken images found in checked pages.
- No button/control text overflow found in checked pages.
- No app console errors found in checked pages.

One browser-extension networking log appeared during browser automation; it was not emitted by this app and did not affect the QA result.
