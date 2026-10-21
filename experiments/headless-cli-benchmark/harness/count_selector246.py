"""Account same-candidate captures using unchanged historical canonicalization; offline only."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import socket


def deny_network(*args, **kwargs):
    raise RuntimeError("Offline tokenizer attempted network access; pre-seed verified cache")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    args = parser.parse_args()
    if not args.cache.is_dir():
        raise ValueError("Explicit pre-existing tiktoken cache directory required")
    if importlib.metadata.version("tiktoken") != "0.12.0":
        raise ValueError("Require historical tiktoken==0.12.0; do not silently install/upgrade")
    os.environ["TIKTOKEN_CACHE_DIR"] = str(args.cache.resolve())
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    socket.create_connection = deny_network
    campaign = json.loads(args.campaign.read_text())
    if campaign["HARNESSES"] != ["candidate-default", "candidate-selected"] or campaign["REPS"] != 5 or campaign["WARMUP"] != 0 or campaign["failures"]:
        raise ValueError("Require complete 5+5 candidate campaign with no failures")
    cleanup = campaign.get("cleanupChecks", [{}])[-1].get("finalCampaignCheck", {})
    if cleanup.get("exit") != 0 or cleanup.get("timedOut") is not False or cleanup.get("stdout", "").strip():
        raise ValueError("Final authoritative campaign container cleanup is missing/failed")
    for arm in campaign["HARNESSES"]:
        runs = campaign["raw"]["short"][arm]
        if len(runs) != 5 or not all(r["valid"] and r["mainRequests"] == 4 for r in runs):
            raise ValueError("Incomplete/invalid candidate captures")
    output = args.campaign.with_name("reference-tokens.json")
    comparison = args.campaign.with_name("selector-comparison.json")
    if output.exists() or comparison.exists():
        raise ValueError("Refuse overwriting accounting results")
    historical = Path(__file__).with_name("count_tokens.py")
    spec = importlib.util.spec_from_file_location("historical_token_accounting", historical)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.analyze(args.campaign, output)
    result = json.loads(output.read_text())
    # Keep the historical module and its accounting unchanged; qualify its generic long-run note.
    result["limitations"].append("This selector campaign is short-only: four main calls, three file reads per session; generic 51-call note above belongs to historical module")
    result["accounting_source_sha256"] = hashlib.sha256(historical.read_bytes()).hexdigest()
    output.write_text(json.dumps(result, indent=2) + "\n")
    default = result["harnesses"]["candidate-default"]["short"]["median"]
    selected = result["harnesses"]["candidate-selected"]["short"]["median"]
    keys = ["first_main_input_tokens_estimate", "session_input_tokens_estimate", "session_output_tokens_estimate", "session_total_tokens_estimate"]
    deltas = {key: {"default": default[key], "selected": selected[key], "selected_minus_default": selected[key] - default[key], "reduction_percent": 100 * (default[key] - selected[key]) / default[key] if default[key] else None} for key in keys}
    passed = selected["first_main_input_tokens_estimate"] < default["first_main_input_tokens_estimate"] and selected["session_input_tokens_estimate"] < default["session_input_tokens_estimate"] and selected["session_total_tokens_estimate"] < default["session_total_tokens_estimate"]
    comparison.write_text(json.dumps({"acceptance_passed": passed, "measurement": "offline reference tokens, not billing/cache/quality", "deltas": deltas, "campaign_sha256": hashlib.sha256(args.campaign.read_bytes()).hexdigest(), "accounting_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}, indent=2) + "\n")
    if not passed:
        raise SystemExit("Selector acceptance failed: no reduction in first-main/session input and total reference tokens")


if __name__ == "__main__":
    main()
