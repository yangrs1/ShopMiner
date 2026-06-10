"""Verify fix with simpler login flow."""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    failed = []
    page.on("requestfailed", lambda req: failed.append(f"  ! FAILED {req.method} {req.url}: {req.failure}"))

    # ===== Test 1: Home page load (no login) =====
    print("=== TEST 1: Visit home page (no login) ===")
    page.goto("http://127.0.0.1:5000/", wait_until="networkidle", timeout=30000)
    time.sleep(2)
    toasts = page.locator(".el-message").all()
    print(f"  Toasts: {len(toasts)}")
    for t in toasts:
        print(f"    - {t.text_content()}")
    products = page.locator(".product-card").count()
    print(f"  Product cards: {products}")

    # ===== Test 2: Login via API and access home =====
    print("\n=== TEST 2: Login via API + visit home ===")
    r = page.request.post("http://127.0.0.1:5000/api/v1/auth/login",
                          data={"email": "customer@shopminer.com", "password": "Customer@123"})
    print(f"  Login: {r.status}")
    j = r.json()
    print(f"  Token: {j['data']['access_token'][:30]}...")

    # Set localStorage
    page.evaluate("""(data) => {
        localStorage.setItem('shopminer_token', data.token);
        localStorage.setItem('shopminer_refresh_token', data.refresh);
        localStorage.setItem('shopminer_user', JSON.stringify(data.user));
    }""", {"token": j['data']['access_token'], "refresh": j['data']['refresh_token'], "user": j['data']['user']})

    # Reload home
    page.goto("http://127.0.0.1:5000/", wait_until="networkidle", timeout=30000)
    time.sleep(3)
    toasts = page.locator(".el-message").all()
    print(f"  Toasts after home reload: {len(toasts)}")
    for t in toasts:
        print(f"    - {t.text_content()}")
    products = page.locator(".product-card").count()
    print(f"  Product cards: {products}")

    # ===== Test 3: Same for admin =====
    print("\n=== TEST 3: Admin login + visit home ===")
    page.evaluate("() => { localStorage.clear(); }")
    r = page.request.post("http://127.0.0.1:5000/api/v1/auth/login",
                          data={"email": "admin@shopminer.com", "password": "Admin@123"})
    print(f"  Login: {r.status}")
    j = r.json()
    page.evaluate("""(data) => {
        localStorage.setItem('shopminer_token', data.token);
        localStorage.setItem('shopminer_refresh_token', data.refresh);
        localStorage.setItem('shopminer_user', JSON.stringify(data.user));
    }""", {"token": j['data']['access_token'], "refresh": j['data']['refresh_token'], "user": j['data']['user']})

    page.goto("http://127.0.0.1:5000/", wait_until="networkidle", timeout=30000)
    time.sleep(3)
    toasts = page.locator(".el-message").all()
    print(f"  Toasts: {len(toasts)}")
    for t in toasts:
        print(f"    - {t.text_content()}")

    print("\n=== Failed requests ===")
    if failed:
        for f in failed:
            if 'fonts.googleapis' not in f:  # ignore font CSP
                print(f)
    else:
        print("  None!")

    browser.close()
