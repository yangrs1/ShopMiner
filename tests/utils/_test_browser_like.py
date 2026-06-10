import requests
import json
import time

BASE = "http://127.0.0.1:5000/api/v1"

# Login
r = requests.post(f"{BASE}/auth/login", json={"email": "customer@shopminer.com", "password": "Customer@123"})
print(f"Login: {r.status_code}")
token = r.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Simulate browser: send Origin, User-Agent, Referer
browser_headers = {
    **headers,
    "Origin": "http://127.0.0.1:5000",
    "Referer": "http://127.0.0.1:5000/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

print("\n=== Test 3 Home endpoints with browser-like headers ===")
for ep in ["products/categories", "analytics/products/hot?limit=8", "products?per_page=8"]:
    t0 = time.time()
    try:
        r = requests.get(f"{BASE}/{ep}", headers=browser_headers, timeout=10)
        ms = (time.time() - t0) * 1000
        print(f"  {ep}: {r.status_code} {ms:.0f}ms len={len(r.content)}")
    except Exception as e:
        print(f"  {ep}: ERR {type(e).__name__}: {e}")

# Now test with same headers as axios would send
print("\n=== Test with axios-like headers ===")
axios_headers = {
    **headers,
    "Origin": "http://127.0.0.1:5000",
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
}
for ep in ["products/categories"]:
    r = requests.get(f"{BASE}/{ep}", headers=axios_headers, timeout=10)
    print(f"  Status: {r.status_code}, ACAO: {r.headers.get('Access-Control-Allow-Origin')}")
    print(f"  All headers: {dict(r.headers)}")
