"""Markdown comparison table from a compare.ts result: median / p90 per harness.

    python3 -I harness/table.py results/<name>.json [results/build-images.json]
"""
import json, math, sys

d = json.load(open(sys.argv[1]))
foot = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
names = d["HARNESSES"]


def st(v):
    v = sorted(x for x in v if isinstance(x, (int, float)) and math.isfinite(x))
    if not v:
        return None
    q = lambda r: v[min(len(v) - 1, math.ceil(r * len(v)) - 1)]
    return q(.5), q(.9)


def cell(kind, name, f, dg=0):
    xs = [x for x in d["raw"].get(kind, {}).get(name, []) if x.get("valid", True)]
    if not xs:
        return "n/a"
    s = st([f(x) for x in xs])
    return "n/a" if s is None else f"{s[0]:.{dg}f} / {s[1]:.{dg}f}"


ROWS = [
    ("`--version` wall, ms (noop container: {noop})", "version", lambda s: s["wall"], 0),
    ("First model request at stub (cold start), trivial, ms", "trivial", lambda s: s["firstRequest"], 0),
    ("First stdout line (any), trivial, ms", "trivial", lambda s: s["firstStdout"], 0),
    ("**First response output**, trivial, ms", "trivial", lambda s: s["firstResponse"], 0),
    ("**First response output**, short, ms", "short", lambda s: s["firstResponse"], 0),
    ("Process exit, trivial, ms", "trivial", lambda s: s["exitAt"], 0),
    ("Process exit, short (3 tools + answer), ms", "short", lambda s: s["exitAt"], 0),
    ("`docker run` wall incl. teardown, short, ms", "short", lambda s: s["wall"], 0),
    ("**Peak container memory** (cgroup memory.peak), trivial, MiB", "trivial", lambda s: s.get("peakCgroupMiB", s.get("peakCgroupMB")), 0),
    ("**Peak container memory** (cgroup memory.peak), short, MiB", "short", lambda s: s.get("peakCgroupMiB", s.get("peakCgroupMB")), 0),
    ("Max RSS of largest process (time -v), trivial, MiB", "trivial", lambda s: None if s["maxRssKB"] is None else s["maxRssKB"] / 1024, 0),
    ("Max RSS of largest process (time -v), short, MiB", "short", lambda s: None if s["maxRssKB"] is None else s["maxRssKB"] / 1024, 0),
    ("Long: peak container memory (cgroup memory.peak), MiB", "long", lambda s: s.get("peakCgroupMiB", s.get("peakCgroupMB")), 0),
    ("Long: peak summed RSS (250 ms samples), MiB", "long", lambda s: s["memory"].get("peakSampledRssMiB", s["memory"].get("peakSampledRssMB")), 0),
    ("Long: growth, cgroup MiB/step", "long", lambda s: s["memory"].get("slopeCgroupMiBPerStep", s["memory"].get("slopeCgroupMBPerStep")), 2),
    ("Long: growth, summed RSS MiB/step", "long", lambda s: s["memory"].get("slopeRssMiBPerStep", s["memory"].get("slopeRssMBPerStep")), 2),
    ("Long: last request body, KiB", "long", lambda s: None if s["memory"]["lastRequestBytes"] is None else s["memory"]["lastRequestBytes"] / 1024, 0),
    ("Long: process exit, ms", "long", lambda s: s["exitAt"], 0),
]

print("| Metric (fresh `docker run --rm`), median / p90 | " + " | ".join(names) + " |")
print("|---" * (1 + len(names)) + "|")
noop = d["raw"].get("version", {}).get("noop(base)")
for label, kind, f, dg in ROWS:
    if kind not in d["raw"]:
        continue
    if "{noop}" in label:
        s = st([x["wall"] for x in noop]) if noop else None
        label = label.format(noop=f"{s[0]:.0f} / {s[1]:.0f}" if s else "n/a")
    print(f"| {label} | " + " | ".join(cell(kind, n, f, dg) for n in names) + " |")


def pay(n, key, scale=1):
    p = d["payloads"].get(n)
    return "n/a" if not p else f"{p[key] / scale:,.0f}"


print("| First request body, UTF-8 bytes | " + " | ".join(pay(n, "bytes") for n in names) + " |")
print("| First request ≈ tokens (code units/4; heuristic, not tokenizer count) | " + " | ".join(pay(n, "approxTokens") for n in names) + " |")
print("| … system prompt chars | " + " | ".join(pay(n, "systemChars") for n in names) + " |")
print("| … tool definition chars | " + " | ".join(pay(n, "toolChars") for n in names) + " |")
print("| … message chars | " + " | ".join(pay(n, "messageChars") for n in names) + " |")
print("| Tools offered | " + " | ".join(str(len(d["payloads"][n]["toolNames"])) if d["payloads"].get(n) else "n/a" for n in names) + " |")
if foot:
    print("| Image size over base, MiB | " + " | ".join(f"{foot[n].get('imageDeltaBytes', foot[n].get('imageDeltaMB', 0) * 2**20) / 2**20:.0f}" if n in foot and ("imageDeltaBytes" in foot[n] or "imageDeltaMB" in foot[n]) else "n/a" for n in names) + " |")
    print("| Installed package / binary, MiB | " + " | ".join(f"{foot[n].get('installedTotalBytes', foot[n].get('installedMB', 0) * 2**20) / 2**20:.0f}" if n in foot and ("installedTotalBytes" in foot[n] or "installedMB" in foot[n]) else "n/a" for n in names) + " |")
aux = lambda n: str(d["raw"]["trivial"][n][0]["auxRequests"]) if d["raw"].get("trivial", {}).get(n) else "n/a"
print("| Extra (non-task) model requests per run | " + " | ".join(aux(n) for n in names) + " |")
for n in names:
    net = d.get("net", {}).get(n)
    if net:
        print(f"\n- **{n}** outbound (benchmarked): {net['benchmarked'] or 'none'}; with defaults ({', '.join(net['switchedOff']) or 'no switches'} unset): {net['defaults'] or 'none'}")
v = d["raw"].get("version", {})
print("\nVersions: " + "; ".join(f"{n}: {v[n][0].get('version', '(stderr)')}" for n in names if v.get(n)))
print(f"n={d['REPS']} per harness (long n={d['LONG_REPS']}, {d['LONG_STEPS']} steps), warmup {d['WARMUP']}, stub latency {d['LATENCY']} ms, --cpus {d['CPUS']} --memory {d['MEMORY']}, failures: {len(d['failures'])}")

if d.get("schemaVersion", 1) >= 2:
    print("\nFixture retention (each measured run; invalid runs excluded from timings):")
    for name in names:
        for kind in ("trivial", "short", "long"):
            samples = d["raw"].get(kind, {}).get(name, [])
            if not samples:
                continue
            counts = {}
            for sample in samples:
                cls = sample.get("fixture", {}).get("contentClass", "unknown") if sample.get("valid") else "invalid"
                counts[cls] = counts.get(cls, 0) + 1
            print(f"- {name}/{kind}: {counts}")
    print("UTF-8 body bytes are measured on the wire; JavaScript UTF-16 code units are retained separately. MiB = 2^20 bytes; KiB = 2^10 bytes.")
