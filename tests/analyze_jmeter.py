"""分析JMeter压测结果"""
import csv
import sys
import os

jtl_path = sys.argv[1] if len(sys.argv) > 1 else "tests/report/jmeter-results.jtl"
if not os.path.isabs(jtl_path):
    jtl_path = os.path.join(os.path.dirname(__file__), "..", jtl_path)

stats = {}
with open(jtl_path, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        label = row["label"]
        elapsed = int(row["elapsed"])
        success = row["success"] == "true"
        if label not in stats:
            stats[label] = {"total": 0, "success": 0, "fail": 0, "times": []}
        stats[label]["total"] += 1
        if success:
            stats[label]["success"] += 1
        else:
            stats[label]["fail"] += 1
        stats[label]["times"].append(elapsed)

header = f"{'接口':<45} {'总数':>5} {'成功':>5} {'失败':>5} {'错误率':>8} {'平均ms':>8} {'P95ms':>8} {'QPS':>8}"
print(header)
print("-" * len(header))
for label, s in sorted(stats.items()):
    times = sorted(s["times"])
    avg = sum(times) / len(times)
    p95 = times[int(len(times) * 0.95)]
    err_rate = s["fail"] / s["total"] * 100
    qps = s["total"] / 10
    row = f"{label:<45} {s['total']:>5} {s['success']:>5} {s['fail']:>5} {err_rate:>7.1f}% {avg:>7.1f} {p95:>7} {qps:>7.1f}"
    print(row)
