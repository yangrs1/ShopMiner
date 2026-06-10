import re
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    content = f.read()
print(f"File size: {len(content)} bytes")
# Find all baseURL patterns
for m in re.finditer(r'base[A-Z][A-Za-z]*:["\'][^"\']+["\']', content):
    print(m.group())
print("---timeout---")
for m in re.finditer(r'timeout:[\d.e+]+', content):
    print(m.group())
print("---/api/ paths---")
for m in re.finditer(r'["\']/api/[^"\']*["\']', content):
    print(m.group())
print("---'api/v1' or 'api' references---")
for m in re.finditer(r'Ot\.post\([^,]+,', content):
    print(m.group())
