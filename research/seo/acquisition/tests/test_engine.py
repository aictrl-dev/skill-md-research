"""Behavioral checks for the local ledger; never perform external actions."""
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


ENGINE_PATH = Path(__file__).resolve().parents[1] / "engine.py"
SPEC = importlib.util.spec_from_file_location("acquisition_engine_under_test", ENGINE_PATH)
engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine)


def evidence(identifier, subject, kind="receipt"):
    return {"id": identifier, "subject_id": subject, "kind": kind,
            "url": f"https://example.test/evidence/{identifier}", "observed_on": "2026-10-22",
            "claim": "Synthetic receipt", "limitation": "Test fixture, no external verification"}


def offer(billing="unknown", amount=None):
    return {"id": "offer-a", "billing": billing, "amount_usd": amount,
            "all_in_verified": False, "duration": "Not verified", "decision": "hold",
            "reason": "Terms need research", "terms_unknown": "Taxes and duration",
            "evidence_ids": ["e-alpha"]}


def source(identifier):
    return {"id": identifier, "name": identifier.title(), "operator_family": identifier,
            "category": "directory", "priority": "P1", "decision": "pursue",
            "status": "candidate", "audience": "Engineering teams", "capabilities": ["skills"],
            "cluster_ids": ["cluster-a"], "asset_ids": ["asset-a"],
            "destination_url": "https://example.test/setup", "hypothesis": "Relevant referrals",
            "eligibility": "Unverified", "link_value": "Unverified", "evidence_ids": [f"e-{identifier}"],
            "status_evidence_ids": [], "live_url": None, "depends_on": [], "offers": [],
            "next_action": {"text": "Research eligibility", "due_on": "2026-10-22",
                            "owner": "qa", "mode": "prepare", "estimated_hours": 1}, "outcomes": []}


def budget(identifier, amount, state="spent"):
    return {"id": identifier, "source_id": "alpha", "evidence_id": "e-alpha",
            "amount_usd": amount, "state": state, "on": "2026-10-22", "note": "Synthetic amount"}


def outcome(evidence_id="e-alpha"):
    return {"window_start": "2026-10-01", "window_end": "2026-10-22", "evidence_id": evidence_id,
            "referred_visitors": None, "qualified_visitors": None, "spend_usd": None,
            "note": "Not measured"}


def ledger():
    """Independent small fixture, not the mutable production research ledger."""
    return {"meta": {"version": 1, "as_of": "2026-10-22", "last_recorded_on": "2026-10-22",
                     "owner": "qa", "nsm": "Evidence-backed relevant visitors",
                     "scope": "research_and_preparation", "partner_budget_usd": 200,
                     "historical_budget_reconciled": False, "search_ads_budget_usd": None,
                     "notes": ["Synthetic test data"]},
            "sources": [source("alpha"), source("beta")],
            "evidence": [evidence("e-alpha", "alpha"), evidence("e-beta", "beta"),
                         evidence("e-global", None, "account_snapshot")],
            "clusters": [{"id": "cluster-a", "name": "Engineering skills", "intent": "Tool research",
                          "priority": "P1", "demand_assessment": "Not measured"}],
            "assets": [{"id": "asset-a", "url": "https://example.test/setup",
                        "readiness": "needs_validation", "gap": "Needs validation", "next_step": "Inspect"}],
            "keywords": [{"id": "keyword-a", "phrase": "engineering skills", "cluster_id": "cluster-a",
                          "intent": "Tool research", "planner": [], "gsc": None,
                          "evidence_ids": ["e-global"], "decision": "research_only", "caveat": "Not measured"}],
            "campaigns": [{"id": "campaign-a", "cluster_id": "cluster-a", "asset_id": "asset-a",
                           "state": "draft_paused", "markets": ["US"], "language": "English",
                           "network": "Google Search only; partners and Display excluded in proposal",
                           "match_types": ["exact", "phrase"], "keywords": ["engineering skills"],
                           "negative_keywords": ["jobs"], "headlines": ["First", "Second", "Third"],
                           "descriptions": ["First description", "Second description"],
                           "budget_usd": None, "max_cpc_usd": None, "launch_blockers": ["No ad budget"]}],
            "events": [{"id": "event-existing", "source_id": "alpha", "evidence_id": "e-alpha",
                        "observed_on": "2026-10-22", "from_status": "candidate",
                        "to_status": "candidate", "note": "Synthetic initial event"}],
            "budget_entries": []}


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.data = ledger()
        engine.validate(self.data)

    def test_independent_valid_fixture_is_not_mutated(self):
        before = copy.deepcopy(self.data)
        engine.validate(self.data)
        self.assertEqual(self.data, before)

    def test_duplicate_ids_rejected_in_every_collection(self):
        for collection in ("sources", "evidence", "clusters", "assets", "keywords", "campaigns", "events", "budget_entries"):
            with self.subTest(collection=collection):
                data = ledger()
                if collection == "budget_entries":
                    data[collection] = [budget("budget-a", 1)]
                data[collection].append(copy.deepcopy(data[collection][0]))
                with self.assertRaises(ValueError):
                    engine.validate(data)

    def test_dangling_foreign_keys_rejected(self):
        paths = [("sources", "evidence_ids"), ("sources", "cluster_ids"), ("sources", "asset_ids"),
                 ("sources", "depends_on"), ("sources", "status_evidence_ids"),
                 ("evidence", "subject_id"), ("keywords", "cluster_id"), ("keywords", "evidence_ids"),
                 ("campaigns", "cluster_id"), ("campaigns", "asset_id"),
                 ("events", "source_id"), ("events", "evidence_id"),
                 ("budget_entries", "source_id"), ("budget_entries", "evidence_id")]
        for collection, field in paths:
            with self.subTest(collection=collection, field=field):
                data = ledger()
                data["budget_entries"] = [budget("budget-a", 1)]
                current = data[collection][0][field]
                data[collection][0][field] = ["missing"] if isinstance(current, list) else "missing"
                with self.assertRaises(ValueError):
                    engine.validate(data)

    def test_offer_evidence_fk_and_duplicate_offer_ids(self):
        for bad in ("missing_evidence", "duplicate_offer"):
            with self.subTest(case=bad):
                data = ledger()
                data["sources"][0]["offers"] = [offer()]
                if bad == "missing_evidence":
                    data["sources"][0]["offers"][0]["evidence_ids"] = ["missing"]
                else:
                    data["sources"][0]["offers"].append(offer())
                with self.assertRaises(ValueError):
                    engine.validate(data)

    def test_self_and_two_source_cycles_rejected(self):
        for two_sources in (False, True):
            with self.subTest(two_sources=two_sources):
                data = ledger()
                data["sources"][0]["depends_on"] = ["beta" if two_sources else "alpha"]
                if two_sources:
                    data["sources"][1]["depends_on"] = ["alpha"]
                with self.assertRaisesRegex(ValueError, "cycle"):
                    engine.validate(data)

    def test_acyclic_dependency_accepted(self):
        self.data["sources"][0]["depends_on"] = ["beta"]
        engine.validate(self.data)

    def test_status_requires_evidence_about_this_source(self):
        for status in ("live", "submitted", "waiting_external"):
            for proof in ([], ["e-beta"], ["e-global"]):
                with self.subTest(status=status, proof=proof):
                    data = ledger()
                    data["sources"][0].update(status=status, status_evidence_ids=proof,
                                              live_url="https://example.test/listing")
                    with self.assertRaises(ValueError):
                        engine.validate(data)

    def test_status_rejects_research_page_as_receipt(self):
        self.data["evidence"][0]["kind"] = "primary"
        self.data["sources"][0].update(status="submitted", status_evidence_ids=["e-alpha"])
        with self.assertRaises(ValueError):
            engine.validate(self.data)

    def test_same_source_receipt_allows_submitted_and_live(self):
        for status in ("submitted", "live"):
            with self.subTest(status=status):
                data = ledger()
                data["sources"][0].update(status=status, status_evidence_ids=["e-alpha"],
                                          live_url="https://example.test/listing" if status == "live" else None)
                engine.validate(data)

    def test_live_requires_public_https_url(self):
        for url in (None, "http://example.test/listing", "not-a-url"):
            with self.subTest(url=url):
                data = ledger()
                data["sources"][0].update(status="live", status_evidence_ids=["e-alpha"], live_url=url)
                with self.assertRaises(ValueError):
                    engine.validate(data)

    def test_explicit_free_zero_accepted_but_unknown_is_not_free(self):
        self.data["sources"][0]["offers"] = [offer("free", 0)]
        engine.validate(self.data)
        for billing, amount in (("free", None), ("free", 1), ("one_time", None)):
            with self.subTest(billing=billing, amount=amount):
                data = ledger()
                data["sources"][0]["offers"] = [offer(billing, amount)]
                with self.assertRaises(ValueError):
                    engine.validate(data)

    def test_unknown_price_remains_null_and_blank_in_export(self):
        self.data["sources"][0]["offers"] = [offer()]
        engine.validate(self.data)
        with tempfile.TemporaryDirectory() as tmp:
            engine.export(self.data, tmp)
            rows = list(csv.DictReader(io.StringIO((Path(tmp) / "offers.csv").read_text())))
        self.assertEqual(rows[0]["billing"], "unknown")
        self.assertEqual(rows[0]["price_usd"], "")
        self.assertIsNone(self.data["sources"][0]["offers"][0]["amount_usd"])

    def test_unknown_offer_cannot_be_classified_free_first(self):
        self.data["sources"][0]["offers"] = [offer()]
        self.data["sources"][0]["offers"][0]["decision"] = "free_first"
        with self.assertRaises(ValueError):
            engine.validate(self.data)

    def test_commitments_plus_spend_cannot_exceed_cumulative_cap(self):
        self.data["budget_entries"] = [budget("b1", 150, "committed_unpaid"), budget("b2", 50.01)]
        with self.assertRaises(ValueError):
            engine.validate(self.data)

    def test_decimal_amounts_exactly_at_cap_are_accepted(self):
        self.data["budget_entries"] = [budget("b1", 199.9, "committed_unpaid"), budget("b2", 0.1)]
        engine.validate(self.data)

    def test_budget_cannot_be_freed_with_negative_or_zero_entries(self):
        for amount in (-10, 0):
            with self.subTest(amount=amount):
                data = ledger()
                data["budget_entries"] = [budget("b1", amount)]
                with self.assertRaises(ValueError):
                    engine.validate(data)

    def test_ad_character_boundaries_and_paused_state(self):
        self.data["campaigns"][0].update(headlines=["H" * 30] * 3, descriptions=["D" * 90] * 2)
        engine.validate(self.data)
        for field, value in (("headlines", ["H" * 31] * 3), ("descriptions", ["D" * 91] * 2),
                             ("state", "enabled")):
            with self.subTest(field=field):
                data = ledger()
                data["campaigns"][0][field] = value
                with self.assertRaises(ValueError):
                    engine.validate(data)

    def test_unknown_historical_balance_is_never_reported_as_available(self):
        for reconciled, expected in ((False, None), (True, 175)):
            with self.subTest(reconciled=reconciled), tempfile.TemporaryDirectory() as tmp:
                data = ledger()
                data["meta"]["historical_budget_reconciled"] = reconciled
                data["budget_entries"] = [budget("b1", 25)]
                path = Path(tmp) / "store.json"
                path.write_text(json.dumps(data))
                output = io.StringIO()
                with patch.object(sys, "argv", [str(ENGINE_PATH), "--store", str(path), "report"]), redirect_stdout(output):
                    engine.main()
                report = json.loads(output.getvalue())
                self.assertEqual(report["available_budget_usd"], expected)
                self.assertEqual(report["recorded_commitments_and_spend_usd"], 25)

    def test_outcome_evidence_must_exist_and_identify_source(self):
        for proof in ("missing", "e-beta"):
            with self.subTest(proof=proof):
                data = ledger()
                data["sources"][0]["outcomes"] = [outcome(proof)]
                with self.assertRaises(ValueError):
                    engine.validate(data)

    def test_event_and_budget_evidence_must_identify_source(self):
        for collection in ("events", "budget_entries"):
            with self.subTest(collection=collection):
                data = ledger()
                data["budget_entries"] = [budget("b1", 1)]
                data[collection][0]["evidence_id"] = "e-beta"
                with self.assertRaises(ValueError):
                    engine.validate(data)


class RecordAndPersistenceTests(unittest.TestCase):
    def test_invalid_record_preserves_caller_including_history(self):
        for changes in ({"status": "invalid"}, {"url": "http://example.test/receipt"},
                        {"observed_on": "2026-02-30"}, {"source_id": "missing"}):
            with self.subTest(changes=changes):
                data = ledger()
                before = copy.deepcopy(data)
                args = dict(source_id="alpha", status="submitted", url="https://example.test/receipt",
                            note="Synthetic receipt", observed_on="2026-10-22")
                args.update(changes)
                with self.assertRaises(ValueError):
                    engine.record(data, **args)
                self.assertEqual(data, before)

    def test_successful_record_returns_valid_independent_ledger(self):
        data = ledger()
        before = copy.deepcopy(data)
        changed = engine.record(data, "alpha", "live", "https://example.test/live", "Synthetic", "2026-10-23")
        engine.validate(changed)
        self.assertEqual(data, before)
        self.assertEqual(changed["sources"][0]["status"], "live")
        self.assertEqual(changed["sources"][0]["live_url"], "https://example.test/live")
        self.assertEqual(changed["meta"]["last_recorded_on"], "2026-10-23")
        self.assertEqual(len(changed["events"]), len(before["events"]) + 1)
        proof = next(e for e in changed["evidence"] if e["id"] == changed["sources"][0]["status_evidence_ids"][0])
        self.assertEqual(proof["subject_id"], "alpha")
        changed["sources"][0]["next_action"]["text"] = "Modified result"
        self.assertEqual(data, before)

    def test_atomic_replace_failure_retains_original_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "store.json"
            original = b'{"original":"unchanged"}\n'
            path.write_bytes(original)
            with patch.object(engine.os, "replace", side_effect=OSError("injected replace failure")):
                with self.assertRaises(OSError):
                    engine.atomic_save({"replacement": True}, path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(set(Path(tmp).iterdir()), {path})

    def test_serialization_failure_does_not_touch_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "store.json"
            path.write_text("original")
            with self.assertRaises(TypeError):
                engine.atomic_save({"invalid": object()}, path)
            self.assertEqual(path.read_text(), "original")
            self.assertEqual(set(Path(tmp).iterdir()), {path})

    def test_atomic_save_success_preserves_unicode_and_replaces_old_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "store.json"
            path.write_text("old")
            data = {"note": "£200 — evidence"}
            engine.atomic_save(data, path)
            self.assertEqual(json.loads(path.read_text()), data)
            self.assertEqual(set(Path(tmp).iterdir()), {path})


class CsvSafetyTests(unittest.TestCase):
    def test_formula_prefixes_including_leading_whitespace_are_escaped(self):
        for value in ("=1+1", "+cmd", "-cmd", "@SUM(A1)", "   =1", " \t+1", "\n=1", "\r@x", "\ttext"):
            with self.subTest(value=value):
                parsed = next(csv.reader(io.StringIO(engine.csv_text([[value]]))))
                self.assertEqual(parsed, ["'" + value])

    def test_nonformula_values_round_trip_with_quotes_newlines_and_null(self):
        values = ["plain", "  ordinary text", "a,b", 'a"b', "line1\nline2", "£200", None, 12, "'=literal"]
        parsed = next(csv.reader(io.StringIO(engine.csv_text([values]))))
        self.assertEqual(parsed, ["" if value is None else str(value) for value in values])

    def test_exports_apply_formula_safety_to_untrusted_source_fields(self):
        data = ledger()
        data["sources"][0]["name"] = "  =HYPERLINK(\"https://example.test\")"
        data["sources"][0]["next_action"]["text"] = "\t+unsafe"
        with tempfile.TemporaryDirectory() as tmp:
            engine.export(data, tmp)
            rows = list(csv.DictReader(io.StringIO((Path(tmp) / "sources.csv").read_text())))
            queue_rows = list(csv.DictReader(io.StringIO((Path(tmp) / "queue.csv").read_text())))
        self.assertEqual(rows[0]["source"], "'" + data["sources"][0]["name"])
        self.assertEqual(rows[0]["next_action"], "'\t+unsafe")
        self.assertEqual(queue_rows[0]["action"], "'\t+unsafe")


if __name__ == "__main__":
    unittest.main()
