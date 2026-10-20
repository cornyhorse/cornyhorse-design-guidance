"""A small, dependency-free benchmark for comparing Python builds (images) on data-transformation-shaped work.

Run it through docs/bench/compare.sh, which runs it in each image, interleaved, several times, and keeps the best
time per test. Never trust a single run: on a laptop running Docker Desktop the same image varies by up to 2x.

Prints one JSON line: {test: best_seconds}. Standard library only.
"""
import json, re, time, sqlite3, csv, io, decimal, datetime, sys, platform, sysconfig, statistics, random

random.seed(1)
def timeit(fn, n=5):
    best = []
    for _ in range(n):
        t = time.perf_counter(); fn(); best.append(time.perf_counter() - t)
    return min(best)

def loops():
    s = 0
    for i in range(3_000_000): s += i * i % 7
    return s
def nbody_like():
    xs = [float(i) for i in range(2000)]
    for _ in range(150):
        xs = [(a * 1.0001 + b * 0.0001) for a, b in zip(xs, xs[1:] + xs[:1])]
def strings():
    out = []
    for i in range(300_000): out.append(f"row-{i}-" + str(i % 97).zfill(3))
    return "|".join(out).upper().split("|")
def dicts():
    d = {}
    for i in range(400_000): d[f"k{i % 5000}"] = d.get(f"k{i % 5000}", 0) + i
    return sorted(d.items(), key=lambda kv: kv[1])
rows = [{"id": i, "name": f"n{i}", "amt": i * 1.5, "tags": ["a", "b", str(i % 9)]} for i in range(60_000)]
def jsonrt(): return json.loads(json.dumps(rows))
text = "\n".join(f"2026-10-{(i%28)+1:02d} user{i%500}@example.com paid {i%900}.{i%100:02d} USD" for i in range(80_000))
pat = re.compile(r"(\d{4}-\d{2}-\d{2}) (\S+)@(\S+) paid ([\d.]+) USD")
def regex(): return [m.groups() for m in pat.finditer(text)]
def decim():
    t = decimal.Decimal(0)
    for i in range(200_000): t += decimal.Decimal(i) / decimal.Decimal(7)
def dates():
    for i in range(60_000): datetime.datetime.strptime(f"2026-10-{(i%28)+1:02d} 12:30", "%Y-%m-%d %H:%M")
def sqlite():
    c = sqlite3.connect(":memory:"); c.execute("create table t(a int, b text, c real)")
    c.executemany("insert into t values (?,?,?)", ((i, f"x{i}", i * 0.5) for i in range(200_000)))
    return c.execute("select b, sum(c) from t group by a % 1000 order by 2 desc").fetchall()
buf = io.StringIO(); w = csv.writer(buf)
for r in rows: w.writerow([r["id"], r["name"], r["amt"]])
data = buf.getvalue()
def csvparse(): return [(int(a), b, float(c)) for a, b, c in csv.reader(io.StringIO(data))]

tests = [loops, nbody_like, strings, dicts, jsonrt, regex, decim, dates, sqlite, csvparse]
print(f"# {sys.version.split()[0]} {platform.machine()} shared={sysconfig.get_config_var('Py_ENABLE_SHARED')}", file=sys.stderr)
print(json.dumps({t.__name__: timeit(t, 12) for t in tests}))
