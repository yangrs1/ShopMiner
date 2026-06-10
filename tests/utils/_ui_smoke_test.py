"""UI smoke test - verify all main pages render and work."""
from playwright.sync_api import sync_playwright
import time

results = []

def check(name, condition, detail=""):
    status = "[OK]" if condition else "[FAIL]"
    results.append((status, name, detail))
    msg = f"  {status} {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)

def section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    failed = []
    page.on("requestfailed", lambda req: failed.append(f"  ! {req.method} {req.url}"))

    # ===== 1. Home page (no login) =====
    section("1. Home Page (anonymous)")
    page.goto("http://127.0.0.1:5000/", wait_until="networkidle", timeout=30000)
    time.sleep(2)
    toasts = page.locator(".el-message").all()
    check("No error toasts", len(toasts) == 0, f"toasts={len(toasts)}")
    products = page.locator(".product-card").count()
    check("Product cards visible", products > 0, f"count={products}")
    has_banner = page.locator("text=ShopMiner").count() > 0
    check("Banner shown", has_banner)

    # ===== 2. Login as customer =====
    section("2. Customer Login + Home")
    r = page.request.post("http://127.0.0.1:5000/api/v1/auth/login",
                          data={"email": "customer@shopminer.com", "password": "Customer@123"})
    j = r.json()
    page.evaluate("""(data) => {
        localStorage.setItem('shopminer_token', data.token);
        localStorage.setItem('shopminer_user', JSON.stringify(data.user));
    }""", {"token": j['data']['access_token'], "user": j['data']['user']})

    page.goto("http://127.0.0.1:5000/", wait_until="networkidle", timeout=30000)
    time.sleep(3)
    toasts = page.locator(".el-message").all()
    check("No error toasts after login", len(toasts) == 0, f"toasts={len(toasts)}")
    products = page.locator(".product-card").count()
    check("Product cards visible", products > 0, f"count={products}")

    # ===== 3. Product Detail =====
    section("3. Product Detail Page")
    # Direct navigation (more reliable than click in headless)
    page.goto("http://127.0.0.1:5000/#/product/5239", wait_until="networkidle", timeout=30000)
    time.sleep(4)
    url = page.url
    check("Navigated to product detail", "/product/" in url, f"url={url}")
    if "/product/" in url:
        has_recommend = page.locator(".rec-reason").count() > 0
        check("Recommendation reason section visible", has_recommend, f"has_recommend={has_recommend}")
        heart = page.locator(".favorite-btn").count()
        check("Favorite button present", heart > 0, f"heart_count={heart}")

    # ===== 4. Cart page =====
    section("4. Cart Page")
    page.goto("http://127.0.0.1:5000/#/cart", wait_until="networkidle", timeout=30000)
    time.sleep(2)
    toasts = page.locator(".el-message").all()
    check("No error toasts on /cart", len(toasts) == 0)
    has_cart = page.locator(".cart-page, .cart-item, h1:has-text('购物车')").count() > 0
    check("Cart page rendered", has_cart)

    # ===== 5. Favorites page =====
    section("5. Favorites Page")
    page.goto("http://127.0.0.1:5000/#/favorites", wait_until="networkidle", timeout=30000)
    time.sleep(2)
    toasts = page.locator(".el-message").all()
    check("No error toasts on /favorites", len(toasts) == 0)
    has_fav = page.locator("h1:has-text('收藏'), h2:has-text('收藏'), .favorites-page").count() > 0
    check("Favorites page rendered", has_fav)

    # ===== 6. Orders page =====
    section("6. Orders Page")
    page.goto("http://127.0.0.1:5000/#/orders", wait_until="networkidle", timeout=30000)
    time.sleep(2)
    toasts = page.locator(".el-message").all()
    check("No error toasts on /orders", len(toasts) == 0)

    # ===== 7. Login as admin =====
    section("7. Admin Login + Admin Page")
    page.evaluate("() => { localStorage.clear(); }")
    r = page.request.post("http://127.0.0.1:5000/api/v1/auth/login",
                          data={"email": "admin@shopminer.com", "password": "Admin@123"})
    j = r.json()
    page.evaluate("""(data) => {
        localStorage.setItem('shopminer_token', data.token);
        localStorage.setItem('shopminer_user', JSON.stringify(data.user));
    }""", {"token": j['data']['access_token'], "user": j['data']['user']})

    page.goto("http://127.0.0.1:5000/#/admin", wait_until="networkidle", timeout=60000)
    time.sleep(5)
    toasts = page.locator(".el-message").all()
    check("No error toasts on /admin", len(toasts) == 0, f"toasts={len(toasts)}")
    url = page.url
    check("Navigated to /admin", "/admin" in url, f"url={url}")
    has_admin = page.locator(".admin-sidebar, .kpi-card, .el-menu").count() > 0
    check("Admin page rendered (sidebar/menu)", has_admin)

    # ===== Failed requests =====
    section("Failed Requests")
    real_failures = [f for f in failed if 'fonts.googleapis' not in f and 'favicon' not in f]
    if real_failures:
        for f in real_failures[:10]:
            print(f)
    else:
        check("No failed requests (excluding fonts)", True)

    # ===== Summary =====
    section("UI Smoke Summary")
    total = len(results)
    passed = sum(1 for s, _, _ in results if s == "[OK]")
    print(f"\n  Total: {total}  Pass: {passed}  Fail: {total - passed}\n")

    browser.close()
