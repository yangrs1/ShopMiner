"""Reproduce user's ERR_NETWORK issue with Playwright."""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Capture all console messages
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))
    # Capture all network requests
    network = []
    page.on("request", lambda req: network.append(f"  > {req.method} {req.url}"))
    page.on("response", lambda res: network.append(f"  < {res.status} {res.url}"))
    page.on("requestfailed", lambda req: network.append(f"  ! FAILED {req.method} {req.url}: {req.failure}"))

    print("=== Loading home page ===")
    page.goto("http://127.0.0.1:5000/", wait_until="networkidle", timeout=30000)
    time.sleep(2)

    print("\n=== Network activity ===")
    for n in network[-30:]:
        print(n)

    print("\n=== Console messages ===")
    for m in console_msgs:
        print(m)

    print("\n=== Login as customer ===")
    page.fill('input[placeholder="请输入邮箱"]', "customer@shopminer.com")
    page.fill('input[type="password"]', "Customer@123")
    page.click('button:has-text("登录")')
    time.sleep(3)

    print("\n=== After login - network ===")
    for n in network[-30:]:
        print(n)

    print("\n=== After login - console ===")
    for m in console_msgs[-10:]:
        print(m)

    print("\n=== After login - check toasts ===")
    toasts = page.locator(".el-message").all()
    for t in toasts:
        print(f"  TOAST: {t.text_content()}")

    browser.close()
