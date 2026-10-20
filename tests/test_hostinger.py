"""Bounded Hostinger transport tests; every request is intercepted locally."""

from contextlib import closing
from hashlib import sha256
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request

from jarvis.hermes import MemPalace
from jarvis.hostinger import (MAX_RESPONSE_BYTES, WEBSITES_URL, _RejectRedirects,
                              list_websites)


def page(data, current=1, total=None, per_page=100):
    return {"data": data, "meta": {"current_page": current, "per_page": per_page,
                                   "total": len(data) if total is None else total}}


class Response(io.BytesIO):
    def __init__(self, value):
        super().__init__(value if isinstance(value, bytes) else json.dumps(value).encode())
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)


class HostingerTests(unittest.TestCase):
    def test_explicit_opt_in_and_valid_token_are_required_before_transport(self):
        opener = Mock()
        for opt_in in (False, None, "true", 1):
            with self.subTest(opt_in=opt_in), self.assertRaises(PermissionError):
                list_websites(allow_external=opt_in, token="synthetic", opener=opener)
        for token in ("", " ", "synthetic\nprivate", "synthetic\x00private", "nonascii-\u2603"):
            with self.subTest(token=token), self.assertRaises(ValueError) as error:
                list_websites(allow_external=True, token=token, opener=opener)
            self.assertNotIn("private", str(error.exception))
        opener.assert_not_called()

    def test_complete_pagination_uses_only_fixed_locally_constructed_urls(self):
        first = page([{"domain": "one.example"}], total=2, per_page=1)
        first["links"] = {"next": "https://untrusted.invalid/steal"}
        responses = [Response(first), Response(page([{"domain": "two.example"}], current=2, total=2, per_page=1))]
        calls = []

        def opener(request, timeout):
            calls.append(request)
            self.assertEqual(15, timeout)
            self.assertEqual("GET", request.get_method())
            self.assertEqual("Bearer synthetic", request.get_header("Authorization"))
            return responses[len(calls) - 1]

        result = list_websites(allow_external=True, token="synthetic", opener=opener)
        self.assertEqual([WEBSITES_URL + "?page=1&per_page=100",
                          WEBSITES_URL + "?page=2&per_page=100"], [request.full_url for request in calls])
        self.assertEqual(["one.example", "two.example"], [site["domain"] for site in result["data"]])
        self.assertEqual({"total": 2, "per_page": 1, "pages_fetched": 2, "complete": True}, result["meta"])
        self.assertEqual("injected", result["transport"])
        self.assertTrue(all(response.closed for response in responses))

    def test_empty_inventory_is_complete_only_with_valid_pagination_metadata(self):
        result = list_websites(allow_external=True, token="synthetic", opener=lambda *_a, **_k: Response(page([])))
        self.assertEqual([], result["data"])
        self.assertIs(result["meta"]["complete"], True)
        self.assertEqual(0, result["meta"]["total"])

    def test_malformed_and_incomplete_pages_fail_closed(self):
        values = [[], {"data": []}, page([None]), page([], total=1),
                  page([], total=-1), page([], current=2), page([], per_page=0),
                  page([], total=True), page([], per_page=101)]
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                list_websites(allow_external=True, token="synthetic",
                              opener=lambda *_a, **_k: Response(value))

    def test_inventory_above_limit_is_not_silently_truncated(self):
        opener = Mock(return_value=Response(page([], total=251)))
        with self.assertRaisesRegex(ValueError, "over-limit"):
            list_websites(allow_external=True, token="synthetic", opener=opener)
        self.assertEqual(1, opener.call_count)

    def test_changing_totals_or_repeated_pages_prevent_complete_result(self):
        first = page([{"domain": "one.example"}], total=2, per_page=1)
        for second in (page([{"domain": "two.example"}], current=2, total=3, per_page=1),
                       page([{"domain": "one.example"}], current=2, total=2, per_page=1)):
            opener = Mock(side_effect=[Response(first), Response(second)])
            with self.subTest(second=second), self.assertRaises(ValueError):
                list_websites(allow_external=True, token="synthetic", opener=opener)

    def test_page_limit_fails_instead_of_returning_partial_inventory(self):
        opener = Mock(return_value=Response(page([{"domain": "one.example"}], total=2, per_page=1)))
        with patch("jarvis.hostinger.MAX_PAGES", 1), self.assertRaisesRegex(ValueError, "page limit"):
            list_websites(allow_external=True, token="synthetic", opener=opener)

    def test_duplicate_records_within_page_do_not_append_success_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = MemPalace(Path(directory) / "memory.sqlite")
            response = Response(page([{"opaque": "one"}, {"opaque": "one"}]))
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                list_websites(allow_external=True, token="synthetic", ledger=ledger,
                              opener=lambda *_a, **_k: response)
            with closing(sqlite3.connect(ledger.path)) as database, database:
                self.assertEqual(0, database.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def test_overlapping_pages_do_not_append_success_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = MemPalace(Path(directory) / "memory.sqlite")
            first = page([{"opaque": "one"}, {"opaque": "two"}], total=4, per_page=2)
            second = page([{"opaque": "two"}, {"opaque": "three"}], current=2, total=4, per_page=2)
            opener = Mock(side_effect=[Response(first), Response(second)])
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                list_websites(allow_external=True, token="synthetic", ledger=ledger, opener=opener)
            with closing(sqlite3.connect(ledger.path)) as database, database:
                self.assertEqual(0, database.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def test_documented_identity_duplicates_reject_different_records(self):
        for key, first_id, second_id in (("domain", "one.example", "ONE.EXAMPLE."),
                                        ("horizons_uuid", "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb",
                                         "AAAAAAAA-1111-2222-3333-BBBBBBBBBBBB")):
            for separate_pages in (False, True):
                with self.subTest(key=key, separate_pages=separate_pages), tempfile.TemporaryDirectory() as directory:
                    ledger = MemPalace(Path(directory) / "memory.sqlite")
                    one, two = {key: first_id, "is_enabled": True}, {key: second_id, "is_enabled": False}
                    bodies = ([page([one], total=2, per_page=1), page([two], current=2, total=2, per_page=1)]
                              if separate_pages else [page([one, two])])
                    opener = Mock(side_effect=[Response(body) for body in bodies])
                    with self.assertRaisesRegex(ValueError, "Duplicate"):
                        list_websites(allow_external=True, token="synthetic", ledger=ledger, opener=opener)
                    with closing(sqlite3.connect(ledger.path)) as database, database:
                        self.assertEqual(0, database.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def test_optional_missing_identity_is_reported_without_snapshot_claim(self):
        result = list_websites(allow_external=True, token="synthetic",
                              opener=lambda *_a, **_k: Response(page([
                                  {"domain": None, "order_id": 1},
                                  {"domain": None, "order_id": 2},
                                  {"domain": "three.example", "horizons_uuid": None}])))
        self.assertEqual(2, result["identity_unavailable_records"])
        self.assertEqual("pagination_totals_and_available_record_identity", result["completeness_basis"])
        self.assertIs(result["transactional_snapshot"], False)

    def test_reads_are_bounded_and_response_is_closed_on_invalid_body(self):
        for body in (b"x" * (MAX_RESPONSE_BYTES + 1), b"\xff", b"", b'{"data":[],"data":[]}',
                     b'{"data":[],"meta":{"total":NaN}}'):
            response = Response(body)
            with self.subTest(size=len(body)), self.assertRaises(RuntimeError):
                list_websites(allow_external=True, token="synthetic",
                              opener=lambda *_a, **_k: response)
            self.assertEqual([MAX_RESPONSE_BYTES + 1], response.read_sizes)
            self.assertTrue(response.closed)

    def test_default_transport_installs_redirect_refusal_and_closes_error(self):
        response = io.BytesIO(b"private-response")
        opener = Mock()
        opener.open.side_effect = HTTPError(WEBSITES_URL, 302, "private-message", {}, response)
        with patch("jarvis.hostinger.build_opener", return_value=opener) as build:
            with self.assertRaises(RuntimeError) as error:
                list_websites(allow_external=True, token="synthetic")
        handler = build.call_args.args[0]
        self.assertIsInstance(handler, _RejectRedirects)
        self.assertIsNone(handler.redirect_request(Request(WEBSITES_URL), None, 302, "redirect", {},
                                                   "https://untrusted.invalid/"))
        self.assertTrue(response.closed)
        self.assertNotIn("private", str(error.exception))
        self.assertEqual(1, opener.open.call_count)

    def test_transport_and_header_error_messages_are_redacted(self):
        opener = Mock(side_effect=ValueError("private-token private-account-response"))
        with self.assertRaises(RuntimeError) as error:
            list_websites(allow_external=True, token="synthetic", opener=opener)
        self.assertEqual("Hostinger inventory request failed", str(error.exception))

    def test_optional_receipt_has_completeness_and_hash_without_account_data(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = MemPalace(Path(directory) / "memory.sqlite")
            result = list_websites(allow_external=True, token="synthetic-private-token", ledger=ledger,
                                  opener=lambda *_a, **_k: Response(page([{"domain": "private-site.example",
                                                                          "username": "private-account"}])))
            receipt = result.pop("receipt")
            events = ledger.history(receipt["run_id"], expected_head=receipt["head_sha256"])
            evidence = events[0]["evidence"]
            serialized = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            self.assertEqual(sha256(serialized).hexdigest(), evidence["report_sha256"])
            self.assertIs(evidence["complete"], True)
            self.assertIs(evidence["shared_sync_established"], False)
            self.assertIs(evidence["transactional_snapshot"], False)
            self.assertEqual(0, evidence["identity_unavailable_records"])
            self.assertEqual("hostinger_account_website_inventory", evidence["scope"])
            self.assertEqual("injected", evidence["transport"])
            self.assertNotIn("private", json.dumps(events))

    def test_incomplete_inventory_does_not_append_success_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = MemPalace(Path(directory) / "memory.sqlite")
            with self.assertRaises(ValueError):
                list_websites(allow_external=True, token="synthetic", ledger=ledger,
                              opener=lambda *_a, **_k: Response(page([], total=1)))
            with closing(sqlite3.connect(ledger.path)) as database, database:
                self.assertEqual(0, database.execute("SELECT COUNT(*) FROM events").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
