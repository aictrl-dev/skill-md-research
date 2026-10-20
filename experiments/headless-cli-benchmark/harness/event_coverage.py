"""Event coverage: score each CLI's JSON event stream against the scripted model's own record (the oracle).

The checklist is fixed before scoring and follows the OpenTelemetry GenAI conventions
(gen_ai.conversation.id, gen_ai.request.model, gen_ai.usage.*, gen_ai.tool.name, gen_ai.tool.call.id).
For the short task (three reads, four model calls) there are 25 facts per run:

  run (5)        session id; model id; run-end event with success; token totals equal the oracle's; final answer
  per call (4x2) tokens for that call equal the oracle's (100 in / 10 out); a timestamp inside the call's window
  per tool (3x4) tool and file match the oracle's call; the oracle's call id; the result (all 20 fixture lines); start and end time or duration

A fact counts only when the stream states it and the value matches the oracle. Values are read by one
small normalizer per CLI, which maps that CLI's documented event fields to the facts above.

  python3 -I harness/event_coverage.py results/token-capture-0.5.4-short.json results/event-coverage-0.5.4.json
"""
import argparse
import json
import re
from pathlib import Path

ORACLE_USAGE = (100, 10)  # token-stub.ts USAGE: what the scripted model reports for every call
FIXTURE_LINE = "alpha beta gamma"
FIXTURE_LINES = 20
HARNESSES = ["aictrl-npm-0.5.4", "pi-1.3-node22", "goose", "codex", "opencode-v2", "hermes"]


def events(path):
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # runner markers (@@RUN, @@EXIT) and non-JSON output
    return out


def ms(value):
    """Epoch seconds or milliseconds, or an ISO string, as epoch milliseconds."""
    if isinstance(value, (int, float)):
        return value * 1000 if value < 1e11 else value
    return None


def normalize(name, evs):
    """One record per run: session, model, run end, totals, per-call usage and time, tools, final text."""
    n = {"session": None, "model": None, "end_ok": False, "totals": None, "calls": [], "tools": {}, "final": None}

    def tool(key):
        return n["tools"].setdefault(key, {"id": None, "name": None, "target": None, "result": None, "timed": False})

    for e in evs:
        t = e.get("type")
        if name.startswith("aictrl"):
            n["session"] = n["session"] or e.get("sessionID")
            if t == "session_start":
                n["model"] = e.get("model")
            if t == "step_finish":
                tok = e["part"].get("tokens") or {}
                n["calls"].append({"usage": (tok.get("input"), tok.get("output")), "at": ms(e.get("timestamp"))})
            if t == "tool_use":
                p = e["part"]; st = p.get("state", {})
                r = tool(p.get("callID")); r.update(id=p.get("callID"), name=p.get("tool"), target=json.dumps(st.get("input")), result=st.get("output"))
                r["timed"] = bool((st.get("time") or {}).get("start") and (st.get("time") or {}).get("end"))
            if t == "text":
                n["final"] = e["part"].get("text")
            if t == "invocation_complete":
                n["end_ok"] = e.get("status") == "completed"
        elif name.startswith("pi"):
            if t == "session":
                n["session"] = e.get("id")
            if t == "turn_end":
                m = e["message"]; u = m.get("usage") or {}
                n["model"] = n["model"] or m.get("model")
                n["calls"].append({"usage": (u.get("input"), u.get("output")), "at": ms(m.get("timestamp"))})
                for c in m.get("content") or []:
                    if c.get("type") == "text" and c.get("text", "").strip():
                        n["final"] = c["text"]
            if t == "tool_execution_start":
                r = tool(e.get("toolCallId")); r.update(id=e.get("toolCallId"), name=e.get("toolName"), target=json.dumps(e.get("args")))
            if t == "tool_execution_end":
                r = tool(e.get("toolCallId"))
                r["result"] = "".join(c.get("text", "") for c in (e.get("result") or {}).get("content") or [])
                r["timed"] = e.get("durationMs") is not None
            if t == "agent_end":
                n["end_ok"] = not e.get("willRetry")
        elif name == "goose":
            if t == "message":
                m = e["message"]; c = m["content"][0]
                n["model"] = n["model"] or ((m.get("metadata") or {}).get("inference") or {}).get("requestedModel")
                if m.get("role") == "assistant":
                    n["calls"].append({"usage": (None, None), "at": ms(m.get("created"))})
                if c.get("type") == "toolRequest":
                    v = (c.get("toolCall") or {}).get("value") or {}
                    r = tool(c.get("id")); r.update(id=c.get("id"), name=v.get("name"), target=json.dumps(v.get("arguments")))
                if c.get("type") == "toolResponse":
                    v = (c.get("toolResult") or {}).get("value") or {}
                    tool(c.get("id"))["result"] = "".join(x.get("text", "") for x in v.get("content") or [])
                if c.get("type") == "text":
                    n["final"] = c.get("text")
            if t == "complete":
                n["end_ok"] = True
                n["totals"] = (e.get("input_tokens"), e.get("output_tokens"))
        elif name == "codex":
            if t == "thread.started":
                n["session"] = e.get("thread_id")
            item = e.get("item") or {}
            if item.get("type") == "command_execution":
                r = tool(item["id"]); r.update(id=item["id"], name="shell", target=item.get("command"))
                if t == "item.completed":
                    r["result"] = item.get("aggregated_output")
            if item.get("type") == "agent_message":
                n["final"] = item.get("text")
            if t == "turn.completed":
                n["end_ok"] = True
                u = e.get("usage") or {}
                n["totals"] = (u.get("input_tokens"), u.get("output_tokens"))
        elif name.startswith("opencode"):
            n["session"] = n["session"] or e.get("sessionID")
            if t == "step_finish":
                tok = e["part"].get("tokens") or {}
                n["calls"].append({"usage": (tok.get("input"), tok.get("output")), "at": ms(e.get("timestamp"))})
            if t == "tool_use":
                p = e["part"]; st = p.get("state", {})
                r = tool(p.get("callID") or p.get("id")); r.update(id=p.get("callID") or p.get("id"), name=p.get("tool"), target=json.dumps(st.get("input")), result=st.get("output"))
                r["timed"] = bool((st.get("time") or {}).get("start") and (st.get("time") or {}).get("end"))
            if t == "text":
                n["final"] = e["part"].get("text")
        elif name == "hermes":
            n["session"] = n["session"] or e.get("session_id")
            if t == "system":
                n["model"] = e.get("model")
            if t in ("tool_use", "text"):
                n["calls"].append({"usage": (None, None), "at": ms(e.get("timestamp"))})
            if t == "tool_use":
                key = f"hermes-{sum(1 for k in n['tools'] if k.startswith('hermes-'))}"
                r = tool(key); r.update(name=e.get("name"), target=json.dumps(e.get("input")))
                r["_start"] = e.get("timestamp")
            if t == "tool_result":
                key = next(k for k in reversed(list(n["tools"])) if n["tools"][k]["result"] is None)
                r = n["tools"][key]; r["result"] = e.get("output")
                r["timed"] = bool(r.pop("_start", None) and e.get("duration_ms") is not None)
            if t == "result":
                n["end_ok"] = e.get("exit_code") == 0
                n["final"] = e.get("text")
                tok = e.get("tokens") or {}
                n["totals"] = (tok.get("input"), tok.get("output"))
    return n


def score(n, oracle):
    """Return {fact: bool} for one run against the oracle's main requests."""
    main = [r for r in oracle if r["kind"] == "main"]
    calls = len(main)
    expected_totals = (ORACLE_USAGE[0] * calls, ORACLE_USAGE[1] * calls)
    facts = {
        "run.session_id": bool(n["session"]),
        "run.model": bool(n["model"]) and "fixture" in str(n["model"]),
        "run.end_success": n["end_ok"],
        "run.token_totals": (n["totals"] or (
            (sum(c["usage"][0] for c in n["calls"]), sum(c["usage"][1] for c in n["calls"]))
            if n["calls"] and all(None not in c["usage"] for c in n["calls"]) else None)) == expected_totals,
        "run.final_answer": (n["final"] or "").strip() == "Done.",
    }
    # Calls are matched in order; a stream with fewer call events than the oracle misses the rest.
    for i, req in enumerate(main):
        c = n["calls"][i] if i < len(n["calls"]) else None
        lo = req["epoch"] - 1000
        hi = req["responseDelivery"]["handlerReturningEpoch"] + 5000
        facts[f"call{i}.tokens"] = bool(c) and c["usage"] == ORACLE_USAGE
        facts[f"call{i}.timestamp"] = bool(c) and c["at"] is not None and lo <= c["at"] <= hi
    issued = [r["response"] for r in main if r["response"]["kind"] == "tool"]
    tools = list(n["tools"].values())
    for i, call in enumerate(issued):
        path = re.search(r"/workspace/[\w.-]+", json.dumps(call["arguments"])).group(0)
        match = next((r for r in tools if r["target"] and path in r["target"]), None)
        facts[f"tool{i}.name_and_target"] = bool(match)
        facts[f"tool{i}.call_id"] = bool(match) and match["id"] == call["callId"]
        facts[f"tool{i}.result"] = bool(match) and (match["result"] or "").count(FIXTURE_LINE) == FIXTURE_LINES
        facts[f"tool{i}.timing"] = bool(match) and match["timed"]
    return facts


def main(campaign_path, output):
    campaign = json.loads(campaign_path.read_text())
    logs = campaign_path.with_name(campaign_path.stem + "-logs")
    result = {"definition": __doc__.strip(), "campaign": str(campaign_path), "oracle_usage_per_call": ORACLE_USAGE, "harnesses": {}}
    for name in HARNESSES:
        runs = []
        for run in campaign["raw"]["short"][name]:
            stem = logs / run["runId"]
            oracle = [json.loads(l) for l in Path(f"{stem}.requests.jsonl").read_text().splitlines()]
            facts = score(normalize(name, events(Path(f"{stem}.stdout.jsonl"))), oracle)
            runs.append({"runId": run["runId"], "facts": facts, "covered": sum(facts.values()), "total": len(facts)})
        covered = [r["covered"] for r in runs]
        if len(set(r["total"] for r in runs)) != 1:
            raise ValueError(f"Fact count differs between runs: {name}")
        if len(set(covered)) != 1:
            print(f"note: {name} coverage varies between runs: {covered}")
        result["harnesses"][name] = {"runs": runs, "covered_min": min(covered), "total": runs[0]["total"],
                                     "coverage_pct_min": round(100 * min(covered) / runs[0]["total"], 1)}
    output.write_text(json.dumps(result, indent=1) + "\n")
    print(f"{'fact':22}" + "".join(f"{h[:9]:>11}" for h in HARNESSES))
    for g in ["run.session_id", "run.model", "run.end_success", "run.token_totals", "run.final_answer", "tokens", "timestamp", "name_and_target", "call_id", "result", "timing"]:
        row = []
        for h in HARNESSES:
            f0 = result["harnesses"][h]["runs"][0]["facts"]
            keys = [k for k in f0 if k == g or k.endswith("." + g) and not k.startswith("run.")]
            row.append(f"{sum(min(r['facts'][k] for r in result['harnesses'][h]['runs']) for k in keys)}/{len(keys)}")
        print(f"{g:22}" + "".join(f"{c:>11}" for c in row))
    print(f"{'COVERAGE':22}" + "".join(f"{result['harnesses'][h]['covered_min']}/{result['harnesses'][h]['total']} {result['harnesses'][h]['coverage_pct_min']:.0f}%".rjust(11) for h in HARNESSES))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    main(options.campaign, options.output)
