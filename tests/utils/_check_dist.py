import re
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    content = f.read()
for m in re.finditer(r'baseURL:"[^"]+"|timeout:[0-9.e+]+', content):
    print(m.group())
print("---")
# Find /api/v1 occurrences
api_v1_count = content.count('/api/v1')
print(f'/api/v1 occurrences: {api_v1_count}')
