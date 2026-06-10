import requests
BASE = 'http://127.0.0.1:5000/api/v1'

r = requests.post(f'{BASE}/auth/login', json={'email': 'admin@shopminer.com', 'password': 'Admin@123'})
print('Admin login:', r.status_code, r.json().get('code'))
token = r.json()['data']['access_token']
headers = {'Authorization': f'Bearer {token}'}

r = requests.get(f'{BASE}/analytics/association/list?per_page=5', headers=headers)
data = r.json()
print('Total rules:', data['data']['total'])
for rule in data['data']['rules'][:3]:
    print(f"Rule: {rule['antecedent']} -> {rule['consequent']} (product_id={rule.get('product_id')})")
    if rule.get('product_id'):
        r2 = requests.get(f'{BASE}/analytics/association/product/{rule["product_id"]}')
        recs = r2.json()['data']['recommendations']
        print(f'  Recs for {rule["product_id"]}: {len(recs)}')
        if recs:
            print(f'  Reason: {recs[0].get("reason", "N/A")[:100]}')
