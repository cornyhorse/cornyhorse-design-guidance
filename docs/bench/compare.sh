#!/usr/bin/env bash
# Compare Python images on the same machine, fairly.
#
#   docs/bench/compare.sh ghcr.io/cornyhorse/python-base:3.14 python:3.14-slim
#   ROUNDS=10 CPUS=2 docs/bench/compare.sh <baseline-image> <other-image> [more images...]
#
# Interleaves the images round by round (so drift hits all of them equally), runs each round in a fresh container,
# and keeps the BEST time per test across rounds. The first image is the baseline; the table shows how many times
# slower each other image is (a number below 1.00 means faster than the baseline).
set -euo pipefail
[ "$#" -ge 2 ] || { echo "usage: $0 <baseline-image> <image> [image...]" >&2; exit 2; }
here="$(cd "$(dirname "$0")" && pwd)"
rounds="${ROUNDS:-6}"; cpus="${CPUS:-2}"
out="$(mktemp -d)"; trap 'rm -rf "$out"' EXIT

for image in "$@"; do
  printf '%s -> ' "$image"
  docker run --rm "$image" python3 -c "import sys,platform;print(sys.version.split()[0], platform.machine())"
done
echo "rounds=$rounds cpus=$cpus"

for round in $(seq 1 "$rounds"); do
  for image in "$@"; do
    docker run --rm --cpus "$cpus" -v "$here:/bench:ro" "$image" python3 /bench/bench.py 2>/dev/null \
      >> "$out/$(echo "$image" | tr '/:@' '___').jsonl"
  done
done

python3 - "$out" "$@" <<'PY'
import json, statistics, sys
out, images = sys.argv[1], sys.argv[2:]
def best(image):
    path = f"{out}/{image.replace('/', '_').replace(':', '_').replace('@', '_')}.jsonl"
    runs = [json.loads(line) for line in open(path)]
    return {k: min(r[k] for r in runs) for k in runs[0]}
results = {image: best(image) for image in images}
base = results[images[0]]
print(f"\n{'test':10s} {'baseline ms':>12s}" + "".join(f"  {i[-24:]:>24s}" for i in images[1:]))
for test in base:
    print(f"{test:10s} {base[test]*1000:12.1f}" + "".join(f"  {results[i][test]/base[test]:>23.2f}x" for i in images[1:]))
print(f"{'geomean':10s} {'':12s}" + "".join(
    f"  {statistics.geometric_mean([results[i][t]/base[t] for t in base]):>23.2f}x" for i in images[1:]))
PY
