"""Comprehensive smoke test for ShopMiner project."""
import requests
import time
import os
import json

BASE = "http://127.0.0.1:5000"
API = f"{BASE}/api/v1"
results = []

def check(name, condition, detail=""):
    status = "[OK]" if condition else "[FAIL]"
    results.append((status, name, detail))
    msg = f"  {status} {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)
    return condition

def section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")

# ===== 1. 服务存活 =====
section("1. Service Health")
try:
    r = requests.get(f"{BASE}/", timeout=5)
    check("Home / returns 200", r.status_code == 200, f"len={len(r.content)}")
    check("Home Content-Type is HTML", 'text/html' in r.headers.get('Content-Type', ''))
except Exception as e:
    check("Home accessible", False, str(e))

# ===== 2. 静态文件 =====
section("2. Static Files")
for path in ['/static/images/default/placeholder_1.jpg', '/assets/index-BiJo78ot.js']:
    try:
        r = requests.get(f"{BASE}{path}", timeout=5)
        check(f"GET {path}", r.status_code == 200, f"len={len(r.content)}")
    except Exception as e:
        check(f"GET {path}", False, str(e))

# ===== 3. 登录 =====
section("3. User Login")
tokens = {}
for email, password, role in [
    ('admin@shopminer.com', 'Admin@123', 'admin'),
    ('customer@shopminer.com', 'Customer@123', 'customer'),
]:
    try:
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=5)
        ok = r.status_code == 200 and r.json().get('code') == 200
        check(f"{role} login", ok, f"status={r.status_code}")
        if ok:
            tokens[role] = r.json()['data']['access_token']
    except Exception as e:
        check(f"{role} login", False, str(e))

# ===== 4. Auth endpoints =====
section("4. Auth Endpoints")
for role, token in tokens.items():
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{API}/auth/me", headers=headers, timeout=5)
        check(f"{role} /auth/me", r.status_code == 200 and r.json()['data']['role'] == role)
    except Exception as e:
        check(f"{role} /auth/me", False, str(e))

# ===== 5. 公共 API =====
section("5. Public APIs")
endpoints = [
    '/products/categories',
    '/products?per_page=8',
    '/analytics/products/hot?limit=8',
    '/products/5239',
]
for ep in endpoints:
    try:
        r = requests.get(f"{API}{ep}", timeout=5)
        check(f"GET {ep}", r.status_code == 200, f"len={len(r.content)}")
    except Exception as e:
        check(f"GET {ep}", False, str(e))

# Dashboard needs auth
r = requests.get(f"{API}/analytics/dashboard", headers={"Authorization": f"Bearer {tokens.get('admin', '')}"}, timeout=5)
check("GET /analytics/dashboard (auth)", r.status_code == 200, f"len={len(r.content)}")

# ===== 6. 用户功能 =====
section("6. User Features (customer)")
h = {"Authorization": f"Bearer {tokens.get('customer', '')}"}
for ep in [
    '/cart',
    '/favorites',
    '/orders',
    '/analytics/user/rfm',
    '/reviews/product/5239',
    '/analytics/association/product/5239',
]:
    try:
        r = requests.get(f"{API}{ep}", headers=h, timeout=5)
        check(f"GET {ep}", r.status_code == 200, f"code={r.json().get('code')}")
    except Exception as e:
        check(f"GET {ep}", False, str(e))

# ===== 7. Admin 端点 =====
section("7. Admin Backend (admin)")
h_admin = {"Authorization": f"Bearer {tokens.get('admin', '')}"}
admin_eps = [
    '/admin/orders',
    '/admin/users',
    '/analytics/rfm/summary',
    '/analytics/sales/trend',
    '/analytics/churn/list',
    '/analytics/association/list',
    '/analytics/metrics',
    '/analytics/viz/Clustering',
    '/analytics/viz/Churn',
    '/analytics/viz/SalesForecast',
    '/analytics/viz/Association',
    '/analytics/admin/last-compute-time',
]
for ep in admin_eps:
    try:
        r = requests.get(f"{API}{ep}", headers=h_admin, timeout=8)
        check(f"GET {ep}", r.status_code == 200, f"code={r.json().get('code')}")
    except Exception as e:
        check(f"GET {ep}", False, str(e))

# ===== 8. 收藏 =====
section("8. Favorites")
h_cust = {"Authorization": f"Bearer {tokens.get('customer', '')}"}
try:
    r = requests.post(f"{API}/favorites", json={"product_id": 5239}, headers=h_cust, timeout=5)
    check("POST /favorites", r.status_code in (200, 201), f"code={r.json().get('code')}")
    r = requests.get(f"{API}/favorites/check/5239", headers=h_cust, timeout=5)
    check("GET /favorites/check/5239", r.json()['data']['favorited'] == True)
    r = requests.delete(f"{API}/favorites/5239", headers=h_cust, timeout=5)
    check("DELETE /favorites/5239", r.status_code == 200)
except Exception as e:
    check("Favorites CRUD", False, str(e))

# ===== 9. CORS 预检 =====
section("9. CORS Preflight")
try:
    r = requests.options(f"{API}/products/categories",
                          headers={"Origin": "http://127.0.0.1:5000",
                                   "Access-Control-Request-Method": "GET",
                                   "Access-Control-Request-Headers": "authorization"},
                          timeout=5)
    acao = r.headers.get("Access-Control-Allow-Origin")
    check("OPTIONS returns 200", r.status_code == 200)
    check("ACAO includes 127.0.0.1:5000", "127.0.0.1:5000" in (acao or ""))
    check("ACAH includes authorization", "authorization" in (r.headers.get("Access-Control-Allow-Headers") or ""))
except Exception as e:
    check("CORS preflight", False, str(e))

# ===== 10. 前端 dist 完整性 =====
section("10. Frontend Dist")
dist_dir = r"C:\Users\35027\Desktop\数据挖掘\ShopMiner\frontend\dist"
required = ['index.html', 'assets', 'static/images/default/placeholder_1.jpg']
for p in required:
    full = os.path.join(dist_dir, p)
    check(f"dist/{p} exists", os.path.exists(full))

if os.path.exists(os.path.join(dist_dir, 'index.html')):
    with open(os.path.join(dist_dir, 'index.html')) as f:
        html = f.read()
    import re
    js_files = re.findall(r'/assets/(index-[^"]+\.js)', html)
    check(f"index.html references index-*.js", len(js_files) > 0, js_files[0] if js_files else "")

# ===== 总结 =====
section("测试总结")
total = len(results)
passed = sum(1 for s, _, _ in results if s == "[OK]")
failed = total - passed
print(f"\n  Total: {total}  Pass: {passed}  Fail: {failed}\n")
if failed > 0:
    print("  Failed items:")
    for s, n, d in results:
        if s == "[FAIL]":
            print(f"    [FAIL] {n} -- {d}")
