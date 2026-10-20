"""Rebuild the unpublished article's figures and HTML preview from saved measurements.

One-time import: python3 build.py --source-dir benchmark --campaign benchmark/results/seven-way-0.5.4.json
Subsequent rebuilds: python3 build.py
Requires matplotlib and Python-Markdown. No Docker or model calls are made.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import markdown
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
# OpenCode 1.19.3 (v1) is still measured by the campaign but left out of the article: upstream development is v2-only.
NAMES = {
    "codex": "Codex 0.163.0",
    "pi-1.3-node22": "pi 1.3.0",
    "aictrl-npm-0.5.4": "aictrl 0.5.4",
    "opencode-v2": "OpenCode 2.1.0",
    "hermes": "Hermes 0.22.2",
    "goose": "Goose 1.55.0",
}
# Build records for images added after the frozen build-images.json, keyed by harness name.
EXTRA_FOOTPRINTS = {"aictrl-npm-0.5.4": "build-aictrl-0.5.4.json", "opencode-v2": "build-opencode-v2.json"}
DATE = "2026-10-20"
DATE_LABEL = "20 Oct 2026"
COLOR = "#16748a"
GOLD = "#bd8b12"
SILVER = "#8c96a1"


def quantile(values, fraction):
    """Match the measurement harness: nearest rank, including its lower median."""
    ordered = sorted(values)
    if not ordered or not all(math.isfinite(x) for x in ordered):
        raise ValueError("Missing or non-finite measurement")
    return ordered[math.ceil(fraction * len(ordered)) - 1]


def ingest(source, memory_campaign=None, campaign=None):
    footprint_name = "build-images.json" if (source / "results" / "build-images.json").exists() else "footprint.json"
    files = {name: source / "results" / name for name in ("compare.json", footprint_name)}
    if campaign:
        # One protocol-3 campaign supplies every scenario; no phases are pooled.
        del files["compare.json"]
        files[campaign.name] = campaign
        for extra in EXTRA_FOOTPRINTS.values():
            files[extra] = source / "results" / extra
    measured = json.loads(campaign.read_text()) if campaign else json.loads(files["compare.json"].read_text())
    footprint = json.loads(files[footprint_name].read_text())
    if campaign:
        if measured.get("protocolVersion") != 3:
            raise ValueError("Campaign must use protocol version 3")
        if measured["failures"]:
            raise ValueError(f"Campaign recorded {len(measured['failures'])} failures")
        footprint.update({name: json.loads((source / "results" / extra).read_text()) for name, extra in EXTRA_FOOTPRINTS.items()})
    schema = measured.get("schemaVersion", 1)
    if schema not in (1, 2):
        raise ValueError(f"Unsupported measurement schema {schema}")
    memory_data = json.loads(memory_campaign.read_text()) if memory_campaign else measured
    if memory_campaign:
        if memory_data.get("protocolVersion") != 3:
            raise ValueError("Corrected memory campaign must use protocol version 3")
        if memory_data["HARNESSES"] != measured["HARNESSES"]:
            raise ValueError("Campaign contenders differ")
        for key in ("LONG_STEPS", "LATENCY", "CPUS", "MEMORY"):
            if memory_data[key] != measured[key]:
                raise ValueError(f"Campaign configuration differs: {key}")
        files["memory-unique-ids.json"] = memory_campaign
    fields = ("firstRequest", "firstResponse", "exitAt", "maxRssKB", "mainRequests", "auxRequests", "exit")
    data = {
        "date": DATE,
        "campaign_schema": schema,
        "campaign_metadata": measured.get("campaignMetadata"),
        "source_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()},
        "configuration": {k: measured[k] for k in ("REPS", "LONG_REPS", "LONG_STEPS", "LATENCY", "WARMUP", "CPUS", "MEMORY")},
        "quantile": "nearest rank ceil(p*n), lower of the middle pair at n=20",
        "memory_units": "MiB (bytes / 2^20); largest-process RSS source is KiB",
        "request_length_units": "UTF-8 bytes and separately recorded UTF-16 code units" if schema == 2 else "UTF-16 code units only; original runner's bytes field was JavaScript body.length",
        "historical_failures": measured["failures"] if memory_campaign else [],
        "memory_failures": memory_data["failures"],
        "scenario_sources": {
            "trivial": f"{campaign.name}: single campaign" if campaign else "compare.json: initial single-response phase",
            "long": f"{campaign.name}: single campaign" if campaign else "memory-unique-ids.json: corrected unique-completion-ID phase" if memory_campaign else "compare.json",
        },
        "memory_campaign_metadata": memory_data.get("campaignMetadata"),
        "memory_protocol_version": memory_data.get("protocolVersion"),
        "memory_configuration": {k: memory_data[k] for k in ("LONG_REPS", "LONG_STEPS", "WARMUP")},
        "harnesses": {},
    }
    for name, label in NAMES.items():
        if name not in measured["HARNESSES"]:
            continue
        scenarios = {}
        attempts = {}
        failed_attempts = {}
        for scenario in ("trivial", "long"):
            phase = memory_data if scenario == "long" else measured
            rows = phase["raw"][scenario][name]
            expected = phase["LONG_REPS"] if scenario == "long" else phase["REPS"]
            if len(rows) != expected:
                raise ValueError(f"Unexpected sample count: {name}/{scenario}")
            good = [r for r in rows if r["exit"] == 0 and r.get("valid") is not False and not r.get("timedOut")]
            if not good or (scenario == "trivial" and len(good) != expected):
                raise ValueError(f"Missing completed samples: {name}/{scenario}")
            attempts[scenario] = {"attempted": len(rows), "completed": len(good)}
            failed_attempts[scenario] = [r for r in rows if r not in good]
            scenarios[scenario] = []
            for row in good:
                item = {k: row[k] for k in fields}
                item["runId"] = row.get("runId")
                item["peakCgroupMiB"] = row["peakCgroupMiB" if schema == 2 else "peakCgroupMB"]
                if schema == 2:
                    item["fixture"] = row["fixture"]
                    item["finalRequestBytes"] = row["finalRequestBytes"]
                    item["finalRequestCodeUnits"] = row["finalRequestCodeUnits"]
                if scenario == "long":
                    memory = row["memory"]
                    item["memory"] = {
                        "peakSampledRssMiB": memory["peakSampledRssMiB" if schema == 2 else "peakSampledRssMB"],
                        "slopeCgroupMiBPerStep": memory["slopeCgroupMiBPerStep" if schema == 2 else "slopeCgroupMBPerStep"],
                        "slopeRssMiBPerStep": memory["slopeRssMiBPerStep" if schema == 2 else "slopeRssMBPerStep"],
                        "lastRequestBytes": memory["lastRequestBytes"] if schema == 2 else None,
                        "lastRequestCodeUnits": row["finalRequestCodeUnits"] if schema == 2 else memory["lastRequestBytes"],
                    }
                scenarios[scenario].append(item)
        raw_payload = measured["payloads"][name]
        package = footprint[name]
        sizes = {
            "imageDeltaMiB": package["imageDeltaBytes"] / 2**20,
            "installedMiB": package["installedTotalBytes"] / 2**20,
            "totalImageMiB": package["totalImageBytes"] / 2**20,
            "baseImageMiB": package["matchingBaseBytes"] / 2**20,
        } if footprint_name == "build-images.json" else {
            "imageDeltaMiB": package["imageDeltaMB"],
            "installedMiB": package["installedMB"],
        }
        data["harnesses"][name] = {
            "label": label,
            "scenarios": scenarios,
            "attempts": attempts,
            "failed_attempts": failed_attempts,
            "payload": {
                **{k: raw_payload[k] for k in ("systemChars", "toolChars", "messageChars")},
                "requestBytes": raw_payload["bytes"] if schema == 2 else None,
                "requestCodeUnits": raw_payload["codeUnits"] if schema == 2 else raw_payload["bytes"],
            },
            "footprint": sizes,
        }
    (ROOT / "sources").mkdir(exist_ok=True)
    (ROOT / "sources" / "measurements.json").write_text(json.dumps(data, indent=2) + "\n")
    if campaign:
        session_metrics(measured, campaign, data["source_sha256"][campaign.name])


def time_breakdown(row, logs):
    """Split one session's elapsed time using the stub's per-request timestamps.

    startup: launch to first main request. model: stub request arrival to its handler returning.
    harness: previous main response returned to next main request arriving (parse, tool, next request).
    shutdown: last main response returned to CLI exit. Stub times are offset onto the run clock
    through the first main request, which both clocks record.
    """
    requests = [json.loads(line) for line in (logs / f"{row['runId']}.requests.jsonl").read_text().splitlines()]
    main = sorted((r for r in requests if r["kind"] == "main"), key=lambda r: r["step"])
    if len(main) != row["mainRequests"]:
        raise ValueError(f"Request log mismatch: {row['runId']}")
    offset = main[0]["at"] - row["firstRequest"]
    turns = [b["at"] - a["responseDelivery"]["handlerReturningAt"] for a, b in zip(main, main[1:])]
    if min(turns) <= 0:
        raise ValueError(f"Overlapping main requests: {row['runId']}")
    return {
        "startup_ms": row["firstRequest"],
        "model_ms": sum(r["responseDelivery"]["handlerReturningAt"] - r["at"] for r in main),
        "harness_between_turns_ms": sum(turns),
        "shutdown_ms": row["exitAt"] - (main[-1]["responseDelivery"]["handlerReturningAt"] - offset),
        "turn_gaps_ms": turns,
    }


def session_metrics(measured, campaign, sha256):
    """Session time, its breakdown and model-call counts from the same campaign's 50-read rows."""
    logs = campaign.with_name(campaign.stem + "-logs")
    out = {
        "source": f"benchmark/results/{campaign.name}",
        "source_sha256": sha256,
        "scenario": f"{measured['LONG_STEPS']} distinct reads followed by final Done",
        "model": "local fixed-50ms scripted stub; usage counters artificial",
        "definition": "model calls include main and auxiliary requests; elapsed is exitAt, before evidence persistence",
        "breakdown_definition": time_breakdown.__doc__.strip(),
        "token_usage": "No provider-reported token usage available; never use synthetic stub usage as measured tokens",
        "harnesses": {},
    }
    for name in NAMES:
        rows = measured["raw"]["long"][name]
        good = [r for r in rows if r["exit"] == 0 and r.get("valid") is not False and not r.get("timedOut")]
        runs = [{"runId": r.get("runId"), "elapsed_ms": r["exitAt"], "main_model_calls": r["mainRequests"],
                 "aux_model_calls": r["auxRequests"], "all_model_calls": r["mainRequests"] + r["auxRequests"],
                 **time_breakdown(r, logs)} for r in good]
        gaps = [gap for r in runs for gap in r["turn_gaps_ms"]]
        out["harnesses"][name] = {
            "completed": len(good),
            "attempted": len(rows),
            "session_elapsed_median_ms": quantile([r["elapsed_ms"] for r in runs], 0.5),
            "main_model_calls_median": quantile([r["main_model_calls"] for r in runs], 0.5),
            "aux_model_calls_median": quantile([r["aux_model_calls"] for r in runs], 0.5),
            "all_model_calls_median": quantile([r["all_model_calls"] for r in runs], 0.5),
            "breakdown_median_ms": {key: quantile([r[key] for r in runs], 0.5) for key in ("startup_ms", "model_ms", "harness_between_turns_ms", "shutdown_ms")},
            "turn_gap_median_ms": quantile(gaps, 0.5),
            "turn_gap_p90_ms": quantile(gaps, 0.9),
            "turn_gaps_counted": len(gaps),
            "runs": runs,
        }
    (ROOT / "sources" / "session-metrics.json").write_text(json.dumps(out, indent=2) + "\n")


def rank_color(y):
    return GOLD if y == 0 else SILVER if y == 1 else COLOR


def figure(title, xlabel, labels, limits=None):
    fig, ax = plt.subplots(figsize=(11, 5.7 + max(0, len(labels) - 4) * 0.65), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_title(title, loc="left", fontsize=16, pad=24, weight="bold")
    ax.set_yticks(range(len(labels)), labels, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, fontsize=11, labelpad=12)
    ax.grid(axis="x", alpha=0.15)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#d6d6d6")
    ax.tick_params(axis="y", length=0, pad=12)
    # Physical-size gold and silver medals outside the first- and second-ranked category labels.
    for rank, (face, edge, ink, label) in enumerate((("#e3b849", GOLD, "#5d4100", "#87610e"), ("#d5dae0", SILVER, "#3b4048", "#4d5560"))):
        if rank >= len(labels):
            break
        ax.get_yticklabels()[rank].set_color(label)
        ax.get_yticklabels()[rank].set_weight("bold")
        ax.scatter([-0.34], [rank], transform=ax.get_yaxis_transform(), s=250,
                   facecolors=face, edgecolors=edge, linewidths=1.5, clip_on=False, zorder=4)
        ax.text(-0.34, rank, str(rank + 1), transform=ax.get_yaxis_transform(),
                ha="center", va="center", weight="bold", fontsize=10, color=ink, clip_on=False, zorder=5)
    if limits:
        ax.set_xlim(*limits)
    fig.subplots_adjust(left=0.26, right=0.92, top=0.77, bottom=0.25)
    return fig, ax


def save(fig, name, footnote):
    fig.text(0.04, 0.11, footnote, fontsize=9, color="#525252", va="top", linespacing=1.6)
    for suffix in ("png", "svg"):
        fig.savefig(ROOT / "charts" / f"{name}.{suffix}", facecolor="white")
    plt.close(fig)


def charts(data):
    (ROOT / "charts").mkdir(exist_ok=True)
    harnesses = list(data["harnesses"].values())
    latency = sorted(harnesses, key=lambda h: quantile([r["firstResponse"] for r in h["scenarios"]["trivial"]], 0.5))
    upper = max(quantile([r["firstResponse"] for r in h["scenarios"]["trivial"]], 0.9) for h in latency) * 1.35
    fig, ax = figure("First response from a fresh container", "Milliseconds from before docker run", [h["label"] for h in latency], (0, upper))
    for y, harness in enumerate(latency):
        values = [r["firstResponse"] for r in harness["scenarios"]["trivial"]]
        median, p90 = quantile(values, 0.5), quantile(values, 0.9)
        color = rank_color(y)
        ax.plot([median, p90], [y, y], color=color, linewidth=3, alpha=0.5)
        ax.scatter([median], [y], s=60, color=color, zorder=4)
        ax.scatter([p90], [y], s=110, edgecolors=color, facecolors="white", linewidths=1.6, zorder=3)
        ax.annotate(f"{median:.0f} / {p90:.0f}", (p90 + upper * 0.02, y), va="center", fontsize=11)
    save(fig, "01-first-response", f"Sorted by median, lowest first; gold and silver mark first and second place. Solid: median. Hollow: p90, not a confidence interval.\nSource: aictrl measurements, {DATE_LABEL}, sources/measurements.json. Cached images; 50 ms scripted model.")

    # A harness that cuts tool output holds a different context, so it is listed last without a medal.
    cut = lambda h: any(r.get("fixture", {}).get("contentClass") == "truncated-or-pruned" for r in h["scenarios"]["long"])
    memory = sorted(harnesses, key=lambda h: (cut(h), quantile([r["peakCgroupMiB"] for r in h["scenarios"]["long"]], 0.5)))
    upper = max(quantile([r["peakCgroupMiB"] for r in h["scenarios"]["long"]], 0.9) for h in memory) * 1.3
    steps = data["configuration"]["LONG_STEPS"]
    fig, ax = figure(f"Peak container memory over {steps} tool steps", "Cgroup memory.peak (MiB)", [h["label"] + (" *" if cut(h) else "") for h in memory], (0, upper))
    for y, harness in enumerate(memory):
        values = [r["peakCgroupMiB"] for r in harness["scenarios"]["long"]]
        median, p90 = quantile(values, 0.5), quantile(values, 0.9)
        color = "#b3b3b3" if cut(harness) else rank_color(y)
        ax.plot([median, p90], [y, y], color=color, linewidth=3, alpha=0.5)
        ax.scatter([median], [y], s=60, color=color, zorder=4)
        ax.scatter([p90], [y], s=110, edgecolors=color, facecolors="white", linewidths=1.6, zorder=3)
        ax.annotate(f"{median:.0f} / {p90:.0f}", (p90 + upper * 0.02, y), va="center", fontsize=11)
    save(fig, "02-long-run-memory", f"Lowest observed median first; gold and silver mark first and second place. * Not ranked: cuts each 48 KB read to its first and last ~80 lines. Cgroup is not RSS.\nCompleted runs only; completion counts in summary.csv. Hollow: p90 (= maximum at n=5). Source: aictrl measurements, {DATE_LABEL}, sources/measurements.json.")

    footprint = sorted(harnesses, key=lambda h: h["footprint"]["imageDeltaMiB"])
    upper = max(h["footprint"]["imageDeltaMiB"] for h in footprint) * 1.2
    fig, ax = figure("Image footprint added by each installation", "Image size above its corresponding base (MiB)", [h["label"] for h in footprint], (0, upper))
    for y, harness in enumerate(footprint):
        value = harness["footprint"]["imageDeltaMiB"]
        ax.barh(y, value, color=rank_color(y), alpha=0.85, height=0.5)
        ax.text(value + upper * 0.02, y, f"{value:.0f}", va="center", fontsize=11)
    save(fig, "03-install-footprint", f"Smallest first; gold and silver mark first and second. Uncompressed local image increment; not download or executable size.\nSource: aictrl measurements, {DATE_LABEL}, sources/measurements.json. Corresponding runtime bases differ.")

    utf8 = data["campaign_schema"] == 2
    key, scale = ("requestBytes", 1024) if utf8 else ("requestCodeUnits", 1000)
    requests = sorted(harnesses, key=lambda h: h["payload"][key])
    upper = max(h["payload"][key] / scale for h in requests) * 1.2
    axis = "JSON request body (KiB, measured UTF-8 bytes)" if utf8 else "JSON string length (thousand UTF-16 code units)"
    fig, ax = figure("First task request sent to the scripted model", axis, [h["label"] for h in requests], (0, upper))
    for y, harness in enumerate(requests):
        value = harness["payload"][key] / scale
        ax.barh(y, value, color=rank_color(y), alpha=0.85, height=0.5)
        ax.text(value + upper * 0.02, y, f"{value:.1f}", va="center", fontsize=11)
    units = "Measured UTF-8 bytes, not tokenizer counts." if utf8 else "UTF-16 code units, not bytes or token counts."
    save(fig, "appendix-request-bytes", f"Smallest first; gold and silver mark first and second. Instructions, toolsets and API serialization differ. {units}\nSource: aictrl benchmark, {DATE_LABEL}, sources/measurements.json.")


def session_chart(session):
    ranked = sorted(session["harnesses"].items(), key=lambda pair: pair[1]["session_elapsed_median_ms"])
    upper = max(quantile([r["elapsed_ms"] / 1000 for r in h["runs"]], .9) for _, h in ranked) * 1.3
    fig, ax = figure("Time to finish the scripted 50-read session", "Seconds from before docker run to CLI exit", [NAMES[name] for name, _ in ranked], (0, upper))
    for y, (_, h) in enumerate(ranked):
        values = [r["elapsed_ms"] / 1000 for r in h["runs"]]
        median, p90 = quantile(values, .5), quantile(values, .9)
        color = rank_color(y)
        ax.plot([median, p90], [y, y], color=color, linewidth=3, alpha=.5)
        ax.scatter([median], [y], s=60, color=color, zorder=4)
        ax.scatter([p90], [y], s=110, edgecolors=color, facecolors="white", linewidths=1.6, zorder=3)
        ax.annotate(f"{median:.2f} / {p90:.2f}", (p90 + upper * .02, y), va="center", fontsize=11)
    save(fig, "05-session-time", f"Solid: median. Hollow: p90 (= max at n=5). 51 scripted main calls; Hermes and OpenCode add one auxiliary call.\nFixed 50 ms local model per call; retained context differs. Source: aictrl, {DATE_LABEL}, sources/session-metrics.json.")

    parts = (("startup_ms", "Start-up to first request", "#9cc7d1"), ("model_ms", "Waiting for the scripted model", "#d9d9d9"),
             ("harness_between_turns_ms", "Harness work between turns", COLOR), ("shutdown_ms", "Shut-down", "#5b5b5b"))
    ranked = sorted(session["harnesses"].items(), key=lambda pair: sum(pair[1]["breakdown_median_ms"].values()))
    upper = max(sum(h["breakdown_median_ms"].values()) for _, h in ranked) / 1000 * 1.3
    fig, ax = figure("Where the 50-read session time goes", "Seconds, median of each component", [NAMES[name] for name, _ in ranked], (0, upper))
    for y, (_, h) in enumerate(ranked):
        left = 0
        for key, label, color in parts:
            width = h["breakdown_median_ms"][key] / 1000
            ax.barh(y, width, left=left, color=color, height=0.5, label=label if y == 0 else None)
            left += width
        ax.text(left + upper * .02, y, f"{h['turn_gap_median_ms']:.0f} ms/turn", va="center", fontsize=11)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=len(parts), fontsize=9, frameon=False, handlelength=1.2)
    ax.set_title(ax.get_title("left"), loc="left", fontsize=16, pad=40, weight="bold")
    save(fig, "06-session-breakdown", f"Components are separate medians, so bars approximate the median session. Label: median harness time between one model response and the next request.\nIncludes response parsing, the tool call and building the next request. Source: aictrl, {DATE_LABEL}, sources/session-metrics.json.")


def text_of(content):
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content)


def first_request_parts(body, encoding):
    """Split the first request: system prompt (system/developer messages and `instructions`),
    tool definitions (canonical JSON), and the remainder of the canonical input count
    (task message, injected context and JSON framing)."""
    payload = json.loads(body)
    turns = payload.get("messages") or payload.get("input") or []
    system = [text_of(t["content"]) for t in turns if t.get("role") in ("system", "developer")]
    if payload.get("instructions"):
        system.insert(0, payload["instructions"])
    tools = json.dumps(payload.get("tools", []), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"system_prompt": sum(len(encoding.encode_ordinary(s)) for s in system), "tool_definitions": len(encoding.encode_ordinary(tools)), "tool_count": len(payload.get("tools", []))}


def ingest_tokens(path, names=NAMES, output="token-estimates.json"):
    """Keep per-session reference-token totals; drop per-request detail, which stays in the benchmark results.
    Adds a first-request breakdown read from the capture's gzip request bodies (needs tiktoken at import only)."""
    import gzip
    import tiktoken
    encoding = tiktoken.get_encoding("o200k_base")
    logs = path.with_name(json.loads(path.read_text())["campaign"].split("/")[-1].removesuffix(".json") + "-logs")
    raw = json.loads(path.read_text())
    out = {key: raw[key] for key in raw if key != "harnesses"}
    out["source"] = f"benchmark/results/{path.name}"
    out["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    out["harnesses"] = {}
    for name in names:
        out["harnesses"][name] = {kind: {**{k: v for k, v in scenario.items() if k != "sessions"},
                                         "sessions": [{k: v for k, v in s.items() if k != "requests"} for s in scenario["sessions"]]}
                                  for kind, scenario in raw["harnesses"][name].items()}
        parts = []
        for session in raw["harnesses"][name]["trivial"]["sessions"]:
            with gzip.open(logs / f"{session['runId']}.requests-with-bodies.jsonl.gz", "rt") as stream:
                main = next(e for e in map(json.loads, stream) if e["kind"] == "main")
            split = first_request_parts(main["body"], encoding)
            parts.append(split)
        # Codex's injected environment context varies by a few tokens between runs; the prompt and tools must not.
        if any(p != parts[0] for p in parts):
            raise ValueError(f"System prompt or tool definitions differ between captures: {name}")
        median = raw["harnesses"][name]["trivial"]["median"]["first_main_input_tokens_estimate"]
        out["harnesses"][name]["first_request_parts"] = {**parts[0], "task_and_framing": median - parts[0]["system_prompt"] - parts[0]["tool_definitions"]}
    out["first_request_parts_definition"] = first_request_parts.__doc__.strip()
    (ROOT / "sources" / output).write_text(json.dumps(out, indent=2) + "\n")


SHORT_VARIANTS = {"aictrl-0.5.4-minimal": "aictrl, pi's 4 tools"}


def ingest_short(paths):
    """Whole-task totals for the short scenario (three 340-byte reads, four main calls), every call counted."""
    out = {"scenario": "short: read notes-0..2 (340 bytes each) once each, then reply", "encoding": "o200k_base", "sources": [], "harnesses": {}}
    for path in paths:
        raw = json.loads(path.read_text())
        out["sources"].append({"path": f"benchmark/results/{path.name}", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for name, scenarios in raw["harnesses"].items():
            if name not in NAMES and name not in SHORT_VARIANTS:
                continue
            short = scenarios["short"]
            if short["completed"] != short["attempted"]:
                raise ValueError(f"Incomplete short captures: {name}")
            out["harnesses"][name] = {"label": NAMES.get(name) or SHORT_VARIANTS[name], "completed": short["completed"], **short["median"]}
    (ROOT / "sources" / "token-estimates-short.json").write_text(json.dumps(out, indent=2) + "\n")


def ingest_per_read(path):
    """History growth per 48 KB read in the 50-read session: next main input minus this main input, over steps 5-44.
    Includes the model's tool call and the wrapped tool result; every capture must agree within 10 tokens."""
    raw = json.loads(path.read_text())
    out = {"definition": ingest_per_read.__doc__.strip(), "encoding": "o200k_base", "source": f"benchmark/results/{path.name}", "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "harnesses": {}}
    for name in NAMES:
        growth = []
        for session in raw["harnesses"][name]["long"]["sessions"]:
            main = [r["input_tokens_estimate"] for r in session["requests"] if r["kind"] == "main"]
            growth += [b - a for a, b in zip(main[5:45], main[6:46])]
        if max(growth) - min(growth) > 10:
            raise ValueError(f"Per-read growth varies: {name}")
        out["harnesses"][name] = {"label": NAMES[name], "tokens_per_read_median": quantile(growth, .5), "min": min(growth), "max": max(growth)}
    (ROOT / "sources" / "token-estimates-per-read.json").write_text(json.dumps(out, indent=2) + "\n")


def token_charts(tokens, data):
    pruned = {name for name, h in data["harnesses"].items() if any(r.get("fixture", {}).get("contentClass") == "truncated-or-pruned" for r in h["scenarios"]["long"])}
    first = sorted(tokens["harnesses"].items(), key=lambda pair: pair[1]["trivial"]["median"]["first_main_input_tokens_estimate"])
    upper = max(h["trivial"]["median"]["first_main_input_tokens_estimate"] for _, h in first) / 1000 * 1.2
    fig, ax = figure("First task request, in tokens", "Thousand tokens (o200k_base reference estimate)", [NAMES[name] for name, _ in first], (0, upper))
    parts = (("system_prompt", "System prompt", COLOR), ("tool_definitions", "Tool definitions", "#9cc7d1"), ("task_and_framing", "Task, injected context, JSON framing", "#d9d9d9"))
    for y, (_, h) in enumerate(first):
        left = 0
        for key, label, color in parts:
            width = h["first_request_parts"][key] / 1000
            ax.barh(y, width, left=left, color=color, height=0.5, label=label if y == 0 else None)
            left += width
        ax.text(left + upper * 0.02, y, f"{left:.1f}k  ({h['first_request_parts']['tool_count']} tools)", va="center", fontsize=11)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=len(parts), fontsize=9, frameon=False, handlelength=1.2)
    ax.set_title(ax.get_title("left"), loc="left", fontsize=16, pad=40, weight="bold")
    save(fig, "04-request-tokens", f"Smallest total first. One tokenizer (o200k_base) for every harness; not provider-reported usage, which adds model-specific framing.\nSource: aictrl token capture, {DATE_LABEL}, sources/token-estimates.json. Median of 5 captures; prompts and tools identical in all.")

    short = json.loads((ROOT / "sources" / "token-estimates-short.json").read_text())["harnesses"]
    ranked = sorted(short.items(), key=lambda pair: pair[1]["session_total_tokens_estimate"])
    upper = max(h["session_total_tokens_estimate"] for _, h in ranked) / 1000 * 1.2
    fig, ax = figure("Tokens for a short task: three small files, four model calls", "Thousand tokens, input and output of every call (o200k_base reference estimate)", [h["label"] for _, h in ranked], (0, upper))
    medal = 0
    for y, (name, h) in enumerate(ranked):
        value = h["session_total_tokens_estimate"] / 1000
        variant = name in SHORT_VARIANTS
        ax.barh(y, value, color="#d9d9d9" if variant else rank_color(medal), alpha=0.85, height=0.5, hatch="//" if variant else None, edgecolor="#9a9a9a" if variant else None, linewidth=0)
        ax.text(value + upper * 0.02, y, f"{value:.1f}k", va="center", fontsize=11)
        if variant:
            ax.get_yticklabels()[y].set_style("italic")
        else:
            medal += 1
    save(fig, "07-short-task-tokens", f"Lowest first; gold and silver mark first and second. Hatched: aictrl with pi's four tools, a configuration variant, not ranked. Each call resends prompt, tools and history.\nSource: aictrl token capture, {DATE_LABEL}, sources/token-estimates-short.json. Median of 3 captures; reference estimate, not provider-reported usage.")


def summary(data):
    with (ROOT / "summary.csv").open("w", newline="") as out:
        writer = csv.writer(out)
        utf8 = data["campaign_schema"] == 2
        writer.writerow(["harness", "response_p50_ms", "response_p90_ms", "long_cgroup_p50_mib", "long_cgroup_p90_mib", "long_sampled_sum_rss_p50_mib", "long_largest_process_rss_p50_mib", "image_increment_mib", "installed_package_mib", "first_request_utf8_bytes" if utf8 else "first_request_utf16_code_units", "long_completed", "long_attempted"])
        ranked = sorted(data["harnesses"].values(), key=lambda h: quantile([r["firstResponse"] for r in h["scenarios"]["trivial"]], 0.5))
        for h in ranked:
            trivial = [r["firstResponse"] for r in h["scenarios"]["trivial"]]
            long = [r["peakCgroupMiB"] for r in h["scenarios"]["long"]]
            rss = [r["memory"]["peakSampledRssMiB"] for r in h["scenarios"]["long"]]
            largest_rss = [r["maxRssKB"] / 1024 for r in h["scenarios"]["long"]]
            attempts = h.get("attempts", {}).get("long", {"completed": len(long), "attempted": len(long)})
            writer.writerow([h["label"], *(round(quantile(xs, q), 3) for xs in (trivial, long) for q in (0.5, 0.9)), round(quantile(rss, 0.5), 3), round(quantile(largest_rss, 0.5), 3), h["footprint"]["imageDeltaMiB"], h["footprint"]["installedMiB"], h["payload"]["requestBytes" if utf8 else "requestCodeUnits"], attempts["completed"], attempts["attempted"]])


def preview():
    draft = ROOT / "article.md"
    if not draft.exists():
        return
    content = markdown.markdown(draft.read_text(), extensions=["tables", "fenced_code"])
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>Headless harness benchmark — unpublished draft</title><style>
body{margin:0;background:#fff;color:#242424;font:18px/1.7 system-ui,sans-serif}main{max-width:850px;margin:auto;padding:40px 24px 80px}h1{font-size:42px;line-height:1.2}h2{line-height:1.3;margin-top:2em}a{color:#07637c}img{max-width:100%;height:auto}table{display:block;overflow-x:auto;border-collapse:collapse;font-size:15px}th,td{border-bottom:1px solid #ddd;padding:10px 14px;text-align:left}blockquote{border-left:3px solid #16748a;margin:24px 0;padding:8px 20px;background:#f4f8f9}code{font-size:.87em}pre{overflow-x:auto}.draft{font-size:14px;padding:10px 14px;background:#fff3cd} @media(max-width:600px){h1{font-size:32px}main{padding:20px 16px}body{font-size:17px}}</style></head><body><main><p class="draft">Unpublished draft · Prepared 20 October 2026 · Data and methodological review required before publication</p>"""
    (ROOT / "preview.html").write_text(page + content + "</main></body></html>\n")


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--source-dir", type=Path)
    args.add_argument("--memory-campaign", type=Path)
    args.add_argument("--campaign", type=Path, help="single protocol-3 campaign for every scenario")
    args.add_argument("--tokens", type=Path, help="count_tokens.py output for the matching token-capture campaign")
    args.add_argument("--tokens-minimal", type=Path, help="count_tokens.py output for aictrl with pi's four tools")
    args.add_argument("--tokens-short", type=Path, nargs="+", help="count_tokens.py outputs for the short-task captures")
    options = args.parse_args()
    if options.source_dir:
        ingest(options.source_dir, options.memory_campaign, options.campaign)
    if options.tokens:
        ingest_tokens(options.tokens)
    if options.tokens_minimal:
        ingest_tokens(options.tokens_minimal, ["aictrl-0.5.4-minimal"], "token-estimates-aictrl-minimal.json")
    if options.tokens:
        ingest_per_read(options.tokens)
    if options.tokens_short:
        ingest_short(options.tokens_short)
    data = json.loads((ROOT / "sources" / "measurements.json").read_text())
    charts(data)
    summary(data)
    session_file = ROOT / "sources" / "session-metrics.json"
    if session_file.exists():
        session_chart(json.loads(session_file.read_text()))
    token_file = ROOT / "sources" / "token-estimates.json"
    if token_file.exists():
        token_charts(json.loads(token_file.read_text()), data)
    preview()
    print("Generated chart PNG/SVG pairs, summary.csv and HTML preview when article.md exists.")
