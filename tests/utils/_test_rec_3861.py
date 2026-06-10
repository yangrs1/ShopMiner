import requests
r = requests.get('http://127.0.0.1:5000/api/v1/analytics/association/product/3861')
data = r.json()['data']['recommendations']
print(f'Recommendations for product 3861: {len(data)}')
for rec in data[:3]:
    name = rec['product']['name'][:30]
    reason = rec['reason'][:80]
    print(f'  Product: {name}')
    print(f'  Reason: {reason}')
