"""Focused checks for local reference-token accounting, never provider usage."""
import contextlib
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

import tiktoken

SPEC = importlib.util.spec_from_file_location("count_tokens", Path(__file__).with_name("count_tokens.py"))
accounting = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(accounting)


class TokenAccountingTests(unittest.TestCase):
    def setUp(self):
        self.encoding = tiktoken.get_encoding("o200k_base")

    def test_transport_controls_and_fake_usage_do_not_change_model_input(self):
        model = {"messages": [{"role": "user", "content": "Explain 東京"}], "tools": [], "response_format": {"type": "json_object"}}
        controlled = {**model, "model": "fixture", "stream": True, "temperature": 0.3, "max_tokens": 1000,
                      "seed": 7, "usage": {"prompt_tokens": 999999999}, "metadata": {"trace": "arbitrary"}}
        self.assertEqual(accounting.input_text(json.dumps(controlled)), accounting.canonical(model))
        self.assertEqual(accounting.input_text(json.dumps(model)), accounting.input_text(json.dumps(controlled)))

    def test_non_ascii_uses_real_encoding_and_preserves_literal_content(self):
        text = "こんにちは世界 👩🏽‍💻 café <|endoftext|>"
        canonical = accounting.input_text(json.dumps({"input": text}))
        self.assertIn(text, canonical)
        self.assertNotIn("\\u", canonical)
        self.assertEqual(self.encoding.decode(self.encoding.encode_ordinary(canonical)), canonical)
        self.assertNotEqual(len(self.encoding.encode_ordinary(canonical)), round(len(canonical) / 4))

    def test_output_counts_exact_text_or_tool_name_and_arguments_only(self):
        self.assertEqual(accounting.output_text({"kind": "text", "text": "Done.\n東京", "usage": {"total_tokens": 1000000}}), "Done.\n東京")
        response = {"kind": "tool", "name": "shell", "arguments": {"command": "printf 'café\\n'", "flag": False}, "callId": "ignored", "usage": 1000000}
        self.assertEqual(accounting.output_text(response), '{"arguments":{"command":"printf \'café\\\\n\'","flag":false},"name":"shell"}')

    def test_repeated_history_auxiliary_calls_and_fake_usage_are_accounted_separately(self):
        first = {"messages": [{"role": "user", "content": "東京"}], "tools": []}
        later = {"messages": [*first["messages"], {"role": "assistant", "content": "earlier answer"}, {"role": "user", "content": "again"}], "tools": []}
        aux = {"input": "Name this conversation", "usage": {"prompt_tokens": 999999999}}
        records = []
        for kind, step, payload, response in [
            ("main", 0, first, {"kind": "tool", "name": "read", "arguments": {"path": "/workspace/big-0.txt"}}),
            ("main", 1, later, {"kind": "text", "text": "Done.", "usage": {"completion_tokens": 999999999}}),
            ("aux", 0, aux, {"kind": "text", "text": "Bench title"}),
        ]:
            body = json.dumps(payload, ensure_ascii=False)
            records.append({"kind": kind, "step": step, "body": body, "bytes": len(body.encode()), "response": response, "usage": {"total_tokens": 999999999}})
        expected_in = sum(len(self.encoding.encode_ordinary(accounting.input_text(r["body"]))) for r in records)
        expected_out = sum(len(self.encoding.encode_ordinary(accounting.output_text(r["response"]))) for r in records)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); campaign = base / "capture.json"; logs = base / "capture-logs"; logs.mkdir()
            raw = {}
            for scenario in ("trivial", "long"):
                run_id = scenario + "-run"
                with gzip.open(logs / (run_id + ".requests-with-bodies.jsonl.gz"), "wt") as stream:
                    stream.write("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n")
                raw[scenario] = {"fixture": [{"valid": True, "runId": run_id, "mainRequests": 2, "auxRequests": 1}]}
            campaign.write_text(json.dumps({"protocolVersion": 3, "HARNESSES": ["fixture"], "REPS": 1, "LONG_REPS": 1, "raw": raw}))
            output = base / "tokens.json"
            with contextlib.redirect_stdout(io.StringIO()):
                accounting.analyze(campaign, output)
            result = json.loads(output.read_text())
            self.assertIn("not provider-reported", result["measurement_type"])
            for scenario in ("trivial", "long"):
                row = result["harnesses"]["fixture"][scenario]
                self.assertEqual(row["completed"], 1)
                session = row["sessions"][0]
                self.assertEqual(session["main_calls"], 2)
                self.assertEqual(session["all_calls"], 3)
                self.assertEqual(session["session_input_tokens_estimate"], expected_in)
                self.assertEqual(session["session_output_tokens_estimate"], expected_out)
                self.assertEqual(session["session_total_tokens_estimate"], expected_in + expected_out)
                self.assertGreater(session["session_input_tokens_estimate"], session["first_main_input_tokens_estimate"])
                self.assertEqual(len(session["requests"]), 3)

    def test_invalid_payload_or_response_fails_explicitly(self):
        for payload in ["[]", '{"model":"fixture","stream":true}']:
            with self.assertRaises(ValueError):
                accounting.input_text(payload)
        with self.assertRaises(ValueError):
            accounting.output_text({"kind": "unexpected"})


if __name__ == "__main__":
    unittest.main()
