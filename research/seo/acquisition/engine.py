#!/usr/bin/env python3
"""Local referral research ledger. Never submits, buys, or contacts anyone."""
import argparse
import csv
import io
import json
import os
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
STATUSES = ("candidate", "prepared", "submitted", "live", "waiting_external", "paused", "rejected")


def read_store(path):
    return json.loads(Path(path).read_text())


def validate(data):
    schema = read_store(ROOT / "store.schema.json")
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data), key=lambda e: str(e.path))
    if errors:
        raise ValueError("; ".join(f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors))
    collections = ("sources", "evidence", "clusters", "assets", "keywords", "campaigns", "events", "budget_entries")
    indices = {}
    for name in collections:
        ids = [item["id"] for item in data[name]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate {name} ID")
        indices[name] = set(ids)

    def refs(values, target, context):
        missing = set(values) - indices[target]
        if missing:
            raise ValueError(f"{context}: unknown {target}: {sorted(missing)}")

    evidence_by_id = {e["id"]: e for e in data["evidence"]}

    def source_evidence(evidence_id, source_id, context):
        refs([evidence_id], "evidence", context)
        if evidence_by_id[evidence_id]["subject_id"] != source_id:
            raise ValueError(f"{context}: evidence must identify source {source_id}")

    for source in data["sources"]:
        for field, target in (("evidence_ids", "evidence"), ("cluster_ids", "clusters"), ("asset_ids", "assets"), ("depends_on", "sources")):
            refs(source[field], target, source["id"])
        if source["status"] in ("live", "submitted", "waiting_external") and not source["status_evidence_ids"]:
            raise ValueError(f"{source['id']}: status requires receipt evidence")
        refs(source["status_evidence_ids"], "evidence", source["id"])
        for evidence_id in source["status_evidence_ids"]:
            proof = evidence_by_id[evidence_id]
            if proof["subject_id"] != source["id"] or proof["kind"] not in ("receipt", "founder_confirmation", "live_page"):
                raise ValueError(f"{source['id']}: receipt must identify this source")
        if source["status"] == "live" and not source["live_url"]:
            raise ValueError(f"{source['id']}: live status requires public URL")
        if source["decision"] == "pursue" and source["next_action"]["mode"] != "prepare":
            raise ValueError(f"{source['id']}: pursue must have a preparation action")
        if len({o["id"] for o in source["offers"]}) != len(source["offers"]):
            raise ValueError(f"{source['id']}: duplicate offer ID")
        for offer in source["offers"]:
            refs(offer["evidence_ids"], "evidence", source["id"])
            if (offer["billing"] in ("free", "one_time") and offer["amount_usd"] is None) or (offer["billing"] == "free" and offer["amount_usd"] != 0):
                raise ValueError(f"{source['id']}: free/fixed offers require an explicit price")
            if offer["decision"] == "free_first" and offer["billing"] != "free":
                raise ValueError(f"{source['id']}: an unknown or paid offer cannot be labeled free-first")
        for outcome in source["outcomes"]:
            source_evidence(outcome["evidence_id"], source["id"], source["id"])
            if outcome["window_start"] > outcome["window_end"]:
                raise ValueError(f"{source['id']}: outcome window ends before it starts")
            if outcome["qualified_visitors"] is not None and outcome["referred_visitors"] is not None and outcome["qualified_visitors"] > outcome["referred_visitors"]:
                raise ValueError(f"{source['id']}: qualified visitors exceed referred visitors")
    for evidence in data["evidence"]:
        if evidence["subject_id"] is not None:
            refs([evidence["subject_id"]], "sources", evidence["id"])
    sources = {s["id"]: s for s in data["sources"]}
    def visit(source_id, trail):
        if source_id in trail:
            raise ValueError(f"Source dependency cycle: {source_id}")
        for parent in sources[source_id]["depends_on"]:
            visit(parent, trail | {source_id})
    for source_id in sources:
        visit(source_id, set())
    for item in data["keywords"]:
        refs([item["cluster_id"]], "clusters", item["id"])
        refs(item["evidence_ids"], "evidence", item["id"])
        for market in item["planner"]:
            lo, hi = market["monthly_low"], market["monthly_high"]
            if (lo is None) != (hi is None) or (lo is not None and lo > hi):
                raise ValueError(f"{item['id']}: invalid demand range")
    for item in data["campaigns"]:
        refs([item["cluster_id"]], "clusters", item["id"])
        refs([item["asset_id"]], "assets", item["id"])
        if any(len(t) > 30 for t in item["headlines"]) or any(len(t) > 90 for t in item["descriptions"]):
            raise ValueError(f"{item['id']}: Google Search ad character limit exceeded")
        if item["state"] != "draft_paused":
            raise ValueError("This preparation ledger cannot enable serving campaigns")
    for item in data["events"]:
        refs([item["source_id"]], "sources", item["id"])
        source_evidence(item["evidence_id"], item["source_id"], item["id"])
    for item in data["budget_entries"]:
        refs([item["source_id"]], "sources", item["id"])
        source_evidence(item["evidence_id"], item["source_id"], item["id"])
    used = sum((Decimal(str(e["amount_usd"])) for e in data["budget_entries"]), Decimal(0))
    if used > Decimal(str(data["meta"]["partner_budget_usd"])):
        raise ValueError("Cumulative partner commitments + spend exceed budget")


def queue(data, as_of, include_holds=False):
    eligible = {"pursue", "maintain", "monitor"}
    if include_holds:
        eligible |= {"hold", "reject"}
    return sorted((s for s in data["sources"] if s["decision"] in eligible and s["next_action"]["due_on"] <= as_of),
                  key=lambda s: (s["priority"], s["next_action"]["due_on"], s["id"]))


def safe_cell(value):
    text = "" if value is None else str(value)
    # Protect spreadsheet imports, including whitespace-prefixed formulas.
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def csv_text(rows):
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    for row in rows:
        writer.writerow([safe_cell(cell) for cell in row])
    return out.getvalue()


def export(data, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    rows = [["id", "source", "category", "priority", "decision", "status", "audience", "clusters", "destination", "due_on", "owner", "next_action", "eligibility", "evidence"]]
    evidence = {e["id"]: e for e in data["evidence"]}
    for s in data["sources"]:
        rows.append([s["id"], s["name"], s["category"], s["priority"], s["decision"], s["status"], s["audience"], "; ".join(s["cluster_ids"]), s["destination_url"], s["next_action"]["due_on"], s["next_action"]["owner"], s["next_action"]["text"], s["eligibility"], "; ".join(evidence[e]["url"] for e in s["evidence_ids"])])
    (destination / "sources.csv").write_text(csv_text(rows))
    rows = [["source_id", "offer_id", "billing", "price_usd", "all_in_verified", "duration", "decision", "reason", "terms_unknown"]]
    for s in data["sources"]:
        for o in s["offers"]:
            rows.append([s["id"], o["id"], o["billing"], o["amount_usd"], o["all_in_verified"], o["duration"], o["decision"], o["reason"], o["terms_unknown"]])
    (destination / "offers.csv").write_text(csv_text(rows))
    rows = [["id", "phrase", "cluster", "market", "monthly_low", "monthly_high", "cpc_low_usd", "cpc_high_usd", "gsc_clicks", "gsc_impressions", "gsc_position", "intent"]]
    for k in data["keywords"]:
        for p in k["planner"] or [{"market": "not_collected", "monthly_low": None, "monthly_high": None, "cpc_low_usd": None, "cpc_high_usd": None}]:
            g = k["gsc"] or {}
            rows.append([k["id"], k["phrase"], k["cluster_id"], p["market"], p["monthly_low"], p["monthly_high"], p["cpc_low_usd"], p["cpc_high_usd"], g.get("clicks"), g.get("impressions"), g.get("position"), k["intent"]])
    (destination / "keywords.csv").write_text(csv_text(rows))
    rows = [["id", "source", "priority", "due_on", "mode", "owner", "action"]]
    for s in queue(data, data["meta"]["as_of"], True):
        a = s["next_action"]
        rows.append([s["id"], s["name"], s["priority"], a["due_on"], a["mode"], a["owner"], a["text"]])
    (destination / "queue.csv").write_text(csv_text(rows))


def record(data, source_id, status, url, note, observed_on):
    # Work on a copy; a failed validation cannot alter the caller's ledger.
    data = json.loads(json.dumps(data))
    source = next((s for s in data["sources"] if s["id"] == source_id), None)
    if source is None:
        raise ValueError(f"Unknown source: {source_id}")
    sequence = len(data["events"]) + 1
    event_id = f"event-{sequence:05d}"
    evidence_id = f"receipt-{sequence:05d}"
    data["evidence"].append({"id": evidence_id, "subject_id": source_id, "kind": "receipt", "url": url,
                            "observed_on": observed_on, "claim": note, "limitation": "Operator-recorded receipt; validation does not independently verify the external page."})
    data["events"].append({"id": event_id, "source_id": source_id, "evidence_id": evidence_id,
                          "observed_on": observed_on, "from_status": source["status"], "to_status": status, "note": note})
    source["status"] = status
    source["status_evidence_ids"] = [evidence_id]
    if status == "live":
        source["live_url"] = url
    data["meta"]["last_recorded_on"] = observed_on
    validate(data)
    return data


def atomic_save(data, path):
    path = Path(path)
    # Serialize before touching the existing file. Replace is atomic on this filesystem.
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=".acquisition-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=ROOT / "store.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    commands.add_parser("report")
    q = commands.add_parser("queue")
    q.add_argument("--as-of", default=date.today().isoformat())
    q.add_argument("--limit", type=int, default=15)
    q.add_argument("--include-holds", action="store_true")
    x = commands.add_parser("export")
    x.add_argument("--directory", type=Path, default=ROOT / "generated")
    r = commands.add_parser("record")
    r.add_argument("source_id")
    r.add_argument("--status", choices=STATUSES, required=True)
    r.add_argument("--url", required=True)
    r.add_argument("--note", required=True)
    r.add_argument("--on", required=True)
    args = parser.parse_args()
    try:
        data = read_store(args.store)
        validate(data)
        if args.command == "validate":
            print(f"Valid: {len(data['sources'])} sources; {len(data['keywords'])} keywords; {len(data['campaigns'])} paused ad groups")
        elif args.command == "queue":
            date.fromisoformat(args.as_of)
            if args.limit < 1:
                raise ValueError("--limit must be positive")
            for s in queue(data, args.as_of, args.include_holds)[:args.limit]:
                print(f"{s['priority']} {s['id']} [{s['next_action']['mode']}] {s['next_action']['text']}")
        elif args.command == "export":
            export(data, args.directory)
            print(f"Exported four CSV files to {args.directory}")
        elif args.command == "record":
            data = record(data, args.source_id, args.status, args.url, args.note, args.on)
            atomic_save(data, args.store)
            print("Local receipt recorded. Regenerate exports; no external action performed.")
        else:
            print(json.dumps({"as_of": data["meta"]["as_of"], "sources": len(data["sources"]),
                              "decisions": dict(Counter(s["decision"] for s in data["sources"])),
                              "statuses": dict(Counter(s["status"] for s in data["sources"])),
                              "partner_ceiling_usd": data["meta"]["partner_budget_usd"],
                              "recorded_commitments_and_spend_usd": float(sum(Decimal(str(e["amount_usd"])) for e in data["budget_entries"])),
                              "historical_budget_reconciled": data["meta"]["historical_budget_reconciled"],
                              "available_budget_usd": None if not data["meta"]["historical_budget_reconciled"] else float(Decimal(str(data["meta"]["partner_budget_usd"])) - sum(Decimal(str(e["amount_usd"])) for e in data["budget_entries"])),
                              "search_ads_budget_usd": data["meta"]["search_ads_budget_usd"]}, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, f"Acquisition ledger error: {error}\n")


if __name__ == "__main__":
    main()
