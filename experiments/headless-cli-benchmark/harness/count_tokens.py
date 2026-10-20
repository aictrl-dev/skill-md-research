"""Offline reference-token estimates from local fixture captures; never provider usage.

Input counts encode canonical JSON containing model-facing request fields, excluding
transport settings. Output counts encode returned text or canonical tool name/args.
Repeated conversation history is counted again on every model call. The same
reference encoding is used for every API/harness; provider framing, cache discounts,
reasoning tokens and production task behavior are not measured.
"""
import argparse
import gzip
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path

import tiktoken

INPUT_FIELDS = ("instructions", "messages", "input", "tools", "response_format", "text")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def input_text(body):
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("Request body must be an object")
    selected = {key: payload[key] for key in INPUT_FIELDS if key in payload}
    if not any(key in selected for key in ("instructions", "messages", "input")):
        raise ValueError("No model input found")
    return canonical(selected)


def output_text(response):
    if response["kind"] == "text":
        return response["text"]
    if response["kind"] == "tool":
        return canonical({"name": response["name"], "arguments": response["arguments"]})
    raise ValueError(f"Unknown response kind: {response['kind']}")


def quantile(values, fraction):
    return sorted(values)[math.ceil(len(values) * fraction) - 1]


def analyze(campaign_path, output_path):
    campaign = json.loads(campaign_path.read_text())
    if campaign.get("protocolVersion") != 3:
        raise ValueError("Expected corrected protocol 3")
    logs = campaign_path.with_suffix("").with_name(campaign_path.stem + "-logs")
    encoding = tiktoken.get_encoding("o200k_base")
    result = {
        "measurement_type": "offline reference-token estimates; not provider-reported usage",
        "encoding": "o200k_base",
        "tiktoken_version": importlib.metadata.version("tiktoken"),
        "input_definition": "Tokenize canonical sorted compact JSON of instructions/messages/input/tools/response_format/text; omit absent fields and all transport controls",
        "output_definition": "Tokenize returned text, or canonical JSON of generated tool name and arguments; exclude event framing and call IDs",
        "session_definition": "Sum each request input and response output including auxiliary calls and any retries; repeated history counted again each call",
        "limitations": ["API-specific model framing and tokenizer differences are unmeasured", "No cache discounts or cache-hit data", "No model-generated reasoning tokens", "Scripted output and 51 main calls; not natural task efficiency", "Stub usage counters are artificial and never used"],
        "campaign": str(campaign_path),
        "campaign_sha256": hashlib.sha256(campaign_path.read_bytes()).hexdigest(),
        "harnesses": {},
    }
    for name in campaign["HARNESSES"]:
        scenarios = {}
        for kind in ("trivial", "long"):
            attempts = campaign["raw"][kind][name]
            expected = campaign["REPS"] if kind == "trivial" else campaign["LONG_REPS"]
            if len(attempts) != expected:
                raise ValueError(f"Incomplete campaign: {name}/{kind}")
            sessions = []
            failed = []
            for run in attempts:
                if not run.get("valid"):
                    failed.append(run["runId"])
                    continue
                log = logs / (run["runId"] + ".requests-with-bodies.jsonl.gz")
                requests = []
                with gzip.open(log, "rt") as stream:
                    for line in stream:
                        event = json.loads(line)
                        if event["kind"] not in ("main", "aux"):
                            continue
                        body = event["body"]
                        if len(body.encode("utf-8")) != event["bytes"]:
                            raise ValueError(f"Body byte mismatch: {log}")
                        incoming = len(encoding.encode_ordinary(input_text(body)))
                        outgoing = len(encoding.encode_ordinary(output_text(event["response"])))
                        requests.append({"kind": event["kind"], "step": event["step"], "request_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(), "input_tokens_estimate": incoming, "output_tokens_estimate": outgoing})
                main = [r for r in requests if r["kind"] == "main"]
                if len(main) != run["mainRequests"] or len(requests) != run["mainRequests"] + run["auxRequests"]:
                    raise ValueError(f"Request count mismatch: {log}")
                total_input = sum(r["input_tokens_estimate"] for r in requests)
                total_output = sum(r["output_tokens_estimate"] for r in requests)
                sessions.append({"runId": run["runId"], "capture_sha256": hashlib.sha256(log.read_bytes()).hexdigest(), "first_main_input_tokens_estimate": main[0]["input_tokens_estimate"], "main_calls": len(main), "all_calls": len(requests), "session_input_tokens_estimate": total_input, "session_output_tokens_estimate": total_output, "session_total_tokens_estimate": total_input + total_output, "requests": requests})
            if not sessions:
                raise ValueError(f"No completed captures: {name}/{kind}")
            keys = ("first_main_input_tokens_estimate", "main_calls", "all_calls", "session_input_tokens_estimate", "session_output_tokens_estimate", "session_total_tokens_estimate")
            scenarios[kind] = {"attempted": len(attempts), "completed": len(sessions), "failed_run_ids": failed, "median": {key: quantile([s[key] for s in sessions], .5) for key in keys}, "p90": {key: quantile([s[key] for s in sessions], .9) for key in keys}, "sessions": sessions}
            print(name, kind, scenarios[kind]["median"], flush=True)
        result["harnesses"][name] = scenarios
    output_path.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    analyze(options.campaign, options.output)
