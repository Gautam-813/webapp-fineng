import argparse
import os
import sys
import tempfile
import uuid

import requests
from sqlalchemy import func, or_

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.models import Cart, ContactInquiry, CustomProjectRequest, License, LicenseCheck, Order, User


PAGINATED_KEYS = {"items", "total", "page", "page_size", "pages", "stats"}


class SmokeTestError(AssertionError):
    pass


def step(message: str) -> None:
    print(f"[smoke] {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeTestError(message)


def require_status(response: requests.Response, expected: int | tuple[int, ...], label: str) -> None:
    expected_values = expected if isinstance(expected, tuple) else (expected,)
    if response.status_code not in expected_values:
        raise SmokeTestError(
            f"{label} returned {response.status_code}, expected {expected_values}: {response.text[:500]}"
        )


def require_paginated(data: dict, label: str) -> None:
    missing = PAGINATED_KEYS.difference(data.keys())
    require(not missing, f"{label} is missing paginated keys: {', '.join(sorted(missing))}")
    require(isinstance(data["items"], list), f"{label} items must be a list")
    require(data["page"] >= 1, f"{label} page must be >= 1")
    require(data["page_size"] >= 1, f"{label} page_size must be >= 1")
    require(data["pages"] >= 1, f"{label} pages must be >= 1")


def require_security_headers(response: requests.Response, label: str) -> None:
    required_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Content-Security-Policy",
    ]
    for header in required_headers:
        require(header in response.headers, f"{label} is missing security header {header}")


def get_json(session: requests.Session, url: str, label: str, **kwargs) -> dict | list:
    response = session.get(url, **kwargs)
    require_status(response, 200, label)
    return response.json()


def cleanup(email: str, session_ids: list[str], order_id: int | None = None) -> None:
    db = SessionLocal()
    try:
        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                db.delete(order)

        email_lower = email.lower()
        users = db.query(User).filter(func.lower(User.email) == email_lower).all()
        for user in users:
            licenses = db.query(License).filter(License.user_id == user.id).all()
            for license_record in licenses:
                db.query(LicenseCheck).filter(LicenseCheck.license_id == license_record.id).delete()
                db.delete(license_record)

            orders = db.query(Order).filter(
                or_(
                    Order.user_id == user.id,
                    func.lower(Order.customer_email) == email_lower,
                )
            ).all()
            for order in orders:
                db.delete(order)

            carts = db.query(Cart).filter(Cart.user_id == user.id).all()
            for cart in carts:
                db.delete(cart)

            db.delete(user)

        for session_id in session_ids:
            carts = db.query(Cart).filter(Cart.session_id == session_id).all()
            for cart in carts:
                db.delete(cart)

        contact_inquiries = db.query(ContactInquiry).filter(func.lower(ContactInquiry.email) == email_lower).all()
        for inquiry in contact_inquiries:
            db.delete(inquiry)

        project_requests = db.query(CustomProjectRequest).filter(func.lower(CustomProjectRequest.email) == email_lower).all()
        for project_request in project_requests:
            db.delete(project_request)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run(args: argparse.Namespace) -> None:
    base_url = args.base_url.rstrip("/")
    run_id = uuid.uuid4().hex[:10]
    customer_email = f"qa.smoke.{run_id}@gmail.com"
    customer_password = f"Smoke{run_id}!"
    guest_session_id = f"smoke-guest-{run_id}"
    customer_session_id = f"smoke-customer-{run_id}"
    smoke_mt_account = f"77{run_id[:6]}"
    created_order_id = None

    public = requests.Session()
    customer = requests.Session()
    admin = requests.Session()
    timeout = args.timeout

    for session in (public, customer, admin):
        session.request = _with_timeout(session.request, timeout)
        session.headers.update({"Origin": base_url, "Referer": f"{base_url}/"})

    try:
        step("checking health and public pages")
        health_response = public.get(f"{base_url}/api/health")
        require_status(health_response, 200, "health")
        require_security_headers(health_response, "health")
        health = health_response.json()
        require(health.get("status") == "healthy", "health endpoint did not return healthy")

        for path in [
            "/",
            "/products",
            "/cart",
            "/checkout",
            "/login",
            "/register",
            "/forgot-password",
            "/about",
            "/contact",
            "/risk-disclaimer",
            "/terms",
            "/privacy-policy",
            "/refund-policy",
        ]:
            response = public.get(f"{base_url}{path}")
            require_status(response, 200, f"public page {path}")
            require("TheFinanceCompany" in response.text or path != "/", f"public page {path} rendered unexpected content")

        step("checking public catalog and product detail")
        catalog = get_json(public, f"{base_url}/api/products?page=1&page_size=6", "product catalog")
        require_paginated(catalog, "product catalog")
        require(catalog["total"] > 0 and catalog["items"], "no active products found; run app/scripts/seed_data.py first")
        product = catalog["items"][0]
        product_id = product["id"]
        product_slug = product["slug"]
        product_name = product["name"]

        detail_api = get_json(public, f"{base_url}/api/products/{product_slug}", "product detail api")
        require(detail_api["id"] == product_id, "product detail api returned the wrong product")

        detail_page = public.get(f"{base_url}/products/{product_slug}")
        require_status(detail_page, 200, "product detail page")
        require(product_name in detail_page.text, "product detail page does not include product name")

        step("checking guest cart behavior")
        response = public.post(
            f"{base_url}/api/cart/items",
            params={"session_id": guest_session_id},
            json={"product_id": product_id, "quantity": 1},
        )
        require_status(response, 201, "guest add to cart")
        cart = get_json(public, f"{base_url}/api/cart", "guest cart", params={"session_id": guest_session_id})
        require(cart["items"], "guest cart did not return any items")
        cart_item_id = cart["items"][0]["item_id"]

        response = public.put(
            f"{base_url}/api/cart/items/{cart_item_id}",
            params={"session_id": guest_session_id},
            json={"quantity": 2},
        )
        require_status(response, 200, "guest update cart item")
        cart = get_json(public, f"{base_url}/api/cart", "guest cart after update", params={"session_id": guest_session_id})
        require(cart["items"][0]["quantity"] == 2, "guest cart quantity did not update")

        response = public.delete(
            f"{base_url}/api/cart/items/{cart_item_id}",
            params={"session_id": guest_session_id},
        )
        require_status(response, 204, "guest remove cart item")
        cart = get_json(public, f"{base_url}/api/cart", "guest cart after remove", params={"session_id": guest_session_id})
        require(cart["items"] == [], "guest cart did not remove item")

        step("checking empty checkout validation")
        response = public.post(
            f"{base_url}/api/checkout",
            json={"customer_name": "Smoke Empty", "customer_email": customer_email, "items": []},
        )
        require_status(response, 422, "empty checkout validation")

        step("checking contact and custom project submissions")
        response = public.post(
            f"{base_url}/api/contact",
            json={
                "name": "Smoke Test Customer",
                "email": customer_email,
                "phone": "",
                "company": "Smoke QA",
                "subject": "Smoke product question",
                "message": "This is a temporary smoke-test contact inquiry.",
                "service_type": "product_support",
            },
        )
        require_status(response, 201, "contact submission")

        response = public.post(
            f"{base_url}/api/custom-project-request",
            json={
                "name": "Smoke Test Customer",
                "email": customer_email,
                "phone": "",
                "company": "Smoke QA",
                "project_type": "Custom Expert Advisor",
                "budget_range": "Under $1,000",
                "timeline": "Flexible",
                "description": "This is a temporary smoke-test custom project request.",
            },
        )
        require_status(response, 201, "custom project submission")

        step("preparing authenticated admin session")
        if not args.skip_admin:
            response = admin.post(
                f"{base_url}/api/auth/login",
                json={"email": args.admin_email, "password": args.admin_password},
            )
            require_status(response, 200, "admin login")
            require(response.json()["user"]["role"] == "admin", "admin login did not return admin role")

        step("checking customer login, checkout, and account history")
        if not args.skip_admin:
            response = admin.post(
                f"{base_url}/api/admin/customers",
                json={
                    "full_name": "Smoke Test Customer",
                    "email": customer_email,
                    "password": customer_password,
                    "role": "customer",
                    "status": "active",
                },
            )
            require_status(response, 201, "admin-created smoke customer")
        else:
            step("skip-admin mode cannot create an active OTP-verified customer; customer account checks are limited")
            return

        response = customer.post(
            f"{base_url}/api/auth/login",
            json={"email": customer_email, "password": customer_password},
        )
        require_status(response, 200, "customer login")
        require(response.json()["user"]["role"] == "customer", "registered user should be customer role")
        require("tfc_token=" in response.headers.get("set-cookie", ""), "customer login did not set auth cookie")

        response = customer.post(
            f"{base_url}/api/cart/items",
            params={"session_id": customer_session_id},
            json={"product_id": product_id, "quantity": 1},
        )
        require_status(response, 201, "customer add to cart")

        response = customer.post(
            f"{base_url}/api/checkout",
            json={
                "customer_name": "Smoke Test Customer",
                "customer_email": customer_email,
                "items": [{"product_id": product_id, "quantity": 1}],
            },
        )
        require_status(response, 200, "demo checkout")
        checkout = response.json()
        created_order_id = int(checkout["order_id"])
        require(checkout["confirmation_url"] == f"/order/confirmation?order_id={created_order_id}", "checkout URL mismatch")

        response = customer.delete(f"{base_url}/api/cart", params={"session_id": customer_session_id})
        require_status(response, 204, "customer clear cart")

        confirmation = customer.get(f"{base_url}{checkout['confirmation_url']}")
        require_status(confirmation, 200, "order confirmation page")
        require(str(created_order_id) in confirmation.text, "order confirmation page did not show order id")

        account_orders = get_json(customer, f"{base_url}/api/account/orders?page=1&page_size=5", "account orders")
        require_paginated(account_orders, "account orders")
        require(
            any(order["id"] == created_order_id and order["status"] == "confirmed" for order in account_orders["items"]),
            "created order was not visible in customer account history",
        )

        for path in ["/account", "/account/orders", "/account/licenses", "/account/profile", "/account/support", "/account/projects"]:
            response = customer.get(f"{base_url}{path}")
            require_status(response, 200, f"customer portal page {path}")

        account_profile = get_json(customer, f"{base_url}/api/account/profile", "account profile")
        require(account_profile["email"] == customer_email, "account profile email mismatch")

        account_projects = get_json(customer, f"{base_url}/api/account/projects?page=1&page_size=5", "account projects")
        require_paginated(account_projects, "account projects")

        account_support = get_json(customer, f"{base_url}/api/account/support?page=1&page_size=5", "account support")
        require_paginated(account_support, "account support")

        if not args.skip_admin:
            step("checking license issue, account binding, and EA validation")
            response = admin.post(
                f"{base_url}/api/admin/licenses",
                json={
                    "user_id": account_profile["id"],
                    "product_id": product_id,
                    "status": "active",
                    "activation_type": "ea_account",
                },
            )
            require_status(response, 201, "admin create license")
            license_data = response.json()
            require(license_data["license_key"].startswith("TFE-"), "generated license key format mismatch")

            account_licenses = get_json(customer, f"{base_url}/api/account/licenses", "account licenses")
            require(account_licenses["items"], "customer account did not show issued license")
            license_id = account_licenses["items"][0]["id"]

            response = customer.put(
                f"{base_url}/api/account/licenses/{license_id}/mt-account",
                json={"mt_account_number": smoke_mt_account},
            )
            require_status(response, 200, "customer bind MT account")

            product_file_content = f"smoke protected product file {run_id}".encode("utf-8")
            with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as handle:
                handle.write(product_file_content)
                temp_product_file = handle.name
            try:
                with open(temp_product_file, "rb") as handle:
                    response = admin.post(
                        f"{base_url}/api/admin/products/{product_id}/file",
                        files={"file": ("smoke-product-file.txt", handle, "text/plain")},
                    )
                require_status(response, 200, "admin upload product file")
                uploaded_file = response.json()
                require(uploaded_file["product_file_name"] == "smoke-product-file.txt", "uploaded product filename mismatch")

                account_licenses = get_json(customer, f"{base_url}/api/account/licenses", "account licenses after file upload")
                license_row = next(item for item in account_licenses["items"] if item["id"] == license_id)
                require(license_row["download_available"] is True, "licensed download was not marked available")

                response = customer.get(f"{base_url}/api/account/licenses/{license_id}/download")
                require_status(response, 200, "licensed product download")
                require(response.content == product_file_content, "downloaded product file content mismatch")
            finally:
                try:
                    os.unlink(temp_product_file)
                except OSError:
                    pass

            response = public.post(
                f"{base_url}/api/licenses/v1/ea/validate",
                json={
                    "license_key": license_data["license_key"],
                    "product_code": product_slug,
                    "mt_account_number": smoke_mt_account,
                    "platform": "MT5",
                    "client_version": "smoke",
                },
            )
            require_status(response, 200, "EA license validation")
            require(response.json()["allowed"] is True, "valid EA license was not allowed")

            response = public.post(
                f"{base_url}/api/licenses/v1/ea/validate",
                json={
                    "license_key": license_data["license_key"],
                    "product_code": product_slug,
                    "mt_account_number": "000000",
                    "platform": "MT5",
                    "client_version": "smoke",
                },
            )
            require_status(response, 200, "EA wrong account validation")
            require(response.json()["allowed"] is False, "wrong MT account should not be allowed")

            response = admin.delete(f"{base_url}/api/admin/products/{product_id}/file")
            require_status(response, 204, "admin delete product file")

            step("checking admin login, pages, and paginated APIs")

            for path in ["/admin", "/admin/products", "/admin/orders", "/admin/licenses", "/admin/inquiries", "/admin/customers", "/admin/categories"]:
                response = admin.get(f"{base_url}{path}")
                require_status(response, 200, f"admin page {path}")

            for path, label in [
                ("/api/admin/products?page=1&page_size=5", "admin products"),
                ("/api/admin/orders?page=1&page_size=5", "admin orders"),
                ("/api/admin/licenses?page=1&page_size=5", "admin licenses"),
                ("/api/admin/customers?page=1&page_size=5", "admin customers"),
                ("/api/admin/inquiries?page=1&page_size=5", "admin inquiries"),
                ("/api/admin/project-requests?page=1&page_size=5", "admin project requests"),
            ]:
                data = get_json(admin, f"{base_url}{path}", label)
                require_paginated(data, label)

            categories = get_json(admin, f"{base_url}/api/admin/categories", "admin categories")
            require(isinstance(categories, list), "admin categories should return a list")

            order_search = get_json(
                admin,
                f"{base_url}/api/admin/orders?search={created_order_id}&page=1&page_size=5",
                "admin order search",
            )
            require_paginated(order_search, "admin order search")
            require(
                any(order["id"] == created_order_id for order in order_search["items"]),
                "admin order search did not find the smoke order",
            )

            inquiry_search = get_json(
                admin,
                f"{base_url}/api/admin/inquiries?search={customer_email}&page=1&page_size=5",
                "admin inquiry search",
            )
            require_paginated(inquiry_search, "admin inquiry search")
            require(
                any(inquiry["email"] == customer_email for inquiry in inquiry_search["items"]),
                "admin inquiry search did not find the smoke inquiry",
            )

            project_search = get_json(
                admin,
                f"{base_url}/api/admin/project-requests?search={customer_email}&page=1&page_size=5",
                "admin project request search",
            )
            require_paginated(project_search, "admin project request search")
            require(
                any(project["email"] == customer_email for project in project_search["items"]),
                "admin project request search did not find the smoke project request",
            )

        step("checking CSRF origin protection")
        response = customer.post(
            f"{base_url}/api/auth/logout",
            headers={"Origin": "https://evil.example", "Referer": "https://evil.example/"},
        )
        require_status(response, 403, "cross-site logout protection")
        response = customer.post(f"{base_url}/api/auth/logout")
        require_status(response, 200, "same-origin logout")

        step("all checks passed")
    finally:
        if args.keep_data:
            step(f"keeping smoke data: customer={customer_email}, order_id={created_order_id}")
        else:
            cleanup(customer_email, [guest_session_id, customer_session_id], created_order_id)
            step("temporary smoke data cleaned up")


def _with_timeout(request_func, timeout: int):
    def wrapped(method, url, **kwargs):
        kwargs.setdefault("timeout", timeout)
        return request_func(method, url, **kwargs)

    return wrapped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an end-to-end smoke test against TheFinanceCompany.")
    parser.add_argument("--base-url", default=os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--admin-email", default=os.getenv("SMOKE_ADMIN_EMAIL", "admin@thefinancecompany.com"))
    parser.add_argument("--admin-password", default=os.getenv("SMOKE_ADMIN_PASSWORD", "admin123"))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("SMOKE_TIMEOUT", "10")))
    parser.add_argument("--skip-admin", action="store_true", help="Skip admin-only screens and APIs.")
    parser.add_argument("--keep-data", action="store_true", help="Do not delete temporary smoke customer/order/cart data.")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except requests.RequestException as exc:
        print(f"[smoke] failed: could not reach the app: {exc}")
        raise SystemExit(1)
    except SmokeTestError as exc:
        print(f"[smoke] failed: {exc}")
        raise SystemExit(1)
