"""Offline arithmetic and local-input tests; all values are illustrative."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from jarvis.studio_economics import (
    ASSUMPTION_FIELDS, INPUT_SCHEMA, MAX_EXPECTED_UNITS, MAX_INPUT_BYTES,
    MAX_MINOR_UNITS, MAX_NAME_CHARACTERS, MAX_PRODUCTION_MINUTES, MAX_SCENARIOS,
    REPORT_SCHEMA, StudioEconomicsError, evaluate_studio_economics,
    load_studio_economics,
)


def example_payload():
    return {
        "schema": INPUT_SCHEMA, "currency": "USD",
        "scenarios": [{"name": f"Hypothetical {units} units", "assumptions": {
            "fixed_cash_cost_minor": 6000, "production_minutes": 240,
            "hourly_value_minor": 2000, "unit_price_minor": 900,
            "per_unit_delivery_cash_cost_minor": 50,
            "variable_fee_basis_points": 500, "expected_units": units,
        }} for units in (10, 25, 50)],
    }


def single_scenario(**overrides):
    value = example_payload()
    value["scenarios"] = value["scenarios"][:1]
    value["scenarios"][0]["assumptions"].update(overrides)
    return value


class StudioEconomicsTests(unittest.TestCase):
    def test_illustrative_pilot_keeps_cash_and_labor_results_distinct(self):
        report = evaluate_studio_economics(example_payload())
        self.assertEqual(REPORT_SCHEMA, report["schema"])
        self.assertEqual("hypothetical_scenarios_only", report["status"])
        self.assertEqual(("USD", "USD_cent"), (report["currency"], report["monetary_unit"]))
        expected = [(9000, 950, 6950, 8050, 2050, -5950),
                    (22500, 2375, 8375, 20125, 14125, 6125),
                    (45000, 4750, 10750, 40250, 34250, 26250)]
        for scenario, amounts in zip(report["scenarios"], expected):
            result = scenario["calculations"]
            self.assertEqual((8000, 14000, 45, 95, 805), tuple(result[field] for field in (
                "production_labor_opportunity_cost_minor", "fixed_cost_including_labor_opportunity_cost_minor",
                "variable_fee_per_unit_minor", "variable_cash_cost_per_unit_minor", "cash_contribution_per_unit_minor")))
            self.assertEqual(amounts, tuple(result[field] for field in (
                "expected_revenue_minor", "expected_variable_cash_cost_minor", "expected_total_cash_cost_minor",
                "expected_cash_contribution_minor", "expected_cash_result_after_fixed_cost_minor",
                "expected_result_after_labor_opportunity_cost_minor")))
            self.assertEqual({"status": "finite", "cash_units": 8, "including_labor_units": 18}, scenario["break_even"])
        qualifications = report["qualifications"]
        self.assertEqual("provided_unverified_assumptions", qualifications["assumptions_status"])
        for field in ("measured_actuals_included", "demand_verified", "rights_verified", "taxes_calculated",
                      "spend_approved", "forecast_guaranteed"):
            self.assertIs(False, qualifications[field])
        exclusions = " ".join(report["methodology"]["exclusions"])
        for concept in ("Taxes", "Refunds", "per-transaction fees", "acquisition cost", "Ongoing labor", "Demand", "rights"):
            self.assertIn(concept, exclusions)

    def test_fee_and_labor_round_up_before_whole_unit_break_even(self):
        value = single_scenario(fixed_cash_cost_minor=174, production_minutes=1, hourly_value_minor=121,
                                unit_price_minor=101, per_unit_delivery_cash_cost_minor=10,
                                variable_fee_basis_points=333, expected_units=3)
        scenario = evaluate_studio_economics(value)["scenarios"][0]
        result = scenario["calculations"]
        self.assertEqual(4, result["variable_fee_per_unit_minor"])
        self.assertEqual(3, result["production_labor_opportunity_cost_minor"])
        self.assertEqual(42, result["expected_variable_cash_cost_minor"])
        self.assertEqual(87, result["expected_cash_result_after_fixed_cost_minor"])
        self.assertEqual(84, result["expected_result_after_labor_opportunity_cost_minor"])
        self.assertEqual({"status": "finite", "cash_units": 2, "including_labor_units": 3}, scenario["break_even"])
        tiny = evaluate_studio_economics(single_scenario(
            fixed_cash_cost_minor=0, production_minutes=0, hourly_value_minor=0,
            unit_price_minor=1, per_unit_delivery_cash_cost_minor=0,
            variable_fee_basis_points=1, expected_units=100))["scenarios"][0]
        self.assertEqual(100, tiny["calculations"]["expected_variable_cash_cost_minor"])
        self.assertEqual("no_finite_break_even", tiny["break_even"]["status"])

    def test_break_even_is_the_first_nonnegative_whole_unit_result(self):
        scenarios = example_payload()["scenarios"]
        scenarios[1]["assumptions"].update(fixed_cash_cost_minor=1610, production_minutes=0)
        scenarios[2]["assumptions"].update(fixed_cash_cost_minor=0, production_minutes=1, hourly_value_minor=1)
        report = evaluate_studio_economics({"schema": INPUT_SCHEMA, "currency": "USD", "scenarios": scenarios})
        for scenario in report["scenarios"]:
            calculations = scenario["calculations"]
            contribution = calculations["cash_contribution_per_unit_minor"]
            for field, cost in (("cash_units", scenario["assumptions"]["fixed_cash_cost_minor"]),
                                ("including_labor_units", calculations["fixed_cost_including_labor_opportunity_cost_minor"])):
                units = scenario["break_even"][field]
                self.assertGreaterEqual(contribution * units - cost, 0)
                if units:
                    self.assertLess(contribution * (units - 1) - cost, 0)

    def test_nonpositive_contribution_never_claims_finite_break_even(self):
        for price, delivery, fee, fixed in ((0, 0, 0, 0), (100, 0, 10_000, 0),
                                           (0, 1, 0, 0), (100, 100, 1000, 500)):
            with self.subTest(price=price, delivery=delivery, fee=fee):
                scenario = evaluate_studio_economics(single_scenario(
                    unit_price_minor=price, per_unit_delivery_cash_cost_minor=delivery,
                    variable_fee_basis_points=fee, fixed_cash_cost_minor=fixed))["scenarios"][0]
                self.assertLessEqual(scenario["calculations"]["cash_contribution_per_unit_minor"], 0)
                self.assertEqual({"status": "no_finite_break_even", "cash_units": None, "including_labor_units": None},
                                 scenario["break_even"])

    def test_zero_units_and_zero_costs_remain_explicit(self):
        scenario = evaluate_studio_economics(single_scenario(
            expected_units=0, fixed_cash_cost_minor=0, production_minutes=0,
            hourly_value_minor=0, per_unit_delivery_cash_cost_minor=0, variable_fee_basis_points=0))["scenarios"][0]
        for field, amount in scenario["calculations"].items():
            if field != "cash_contribution_per_unit_minor":
                self.assertEqual(0, amount)
        self.assertEqual({"status": "finite", "cash_units": 0, "including_labor_units": 0}, scenario["break_even"])
        with_fixed = evaluate_studio_economics(single_scenario(expected_units=0))["scenarios"][0]["calculations"]
        self.assertEqual(-6000, with_fixed["expected_cash_result_after_fixed_cost_minor"])
        self.assertEqual(-14000, with_fixed["expected_result_after_labor_opportunity_cost_minor"])

    def test_schema_rejects_actuals_unknown_fields_and_wrong_shapes(self):
        invalid = [None, [], {}, {**example_payload(), "schema": "unknown"},
                   {**example_payload(), "currency": "EUR"}, {**example_payload(), "currency": "usd"},
                   {**example_payload(), "actuals": {"sales": 10}},
                   {**example_payload(), "scenarios": []}, {**example_payload(), "scenarios": {}},
                   {**example_payload(), "scenarios": [None]}]
        for level in ("root", "scenario", "assumptions"):
            value = single_scenario()
            target = value if level == "root" else value["scenarios"][0]
            if level == "assumptions":
                target = target["assumptions"]
            target["approved"] = True
            invalid.append(value)
        for field in ASSUMPTION_FIELDS:
            value = single_scenario()
            del value["scenarios"][0]["assumptions"][field]
            invalid.append(value)
        for index, value in enumerate(invalid):
            with self.subTest(case=index), self.assertRaisesRegex(StudioEconomicsError, "^Invalid studio economics assumptions$"):
                evaluate_studio_economics(value)

    def test_numeric_inputs_reject_bools_floats_nonfinite_negative_and_out_of_bounds(self):
        limits = {"production_minutes": MAX_PRODUCTION_MINUTES, "expected_units": MAX_EXPECTED_UNITS,
                  "variable_fee_basis_points": 10_000}
        for field in ASSUMPTION_FIELDS:
            for value in (True, False, 1.0, float("nan"), float("inf"), -1, "10", None,
                          limits.get(field, MAX_MINOR_UNITS) + 1, 10 ** 100):
                with self.subTest(field=field, value_type=type(value).__name__):
                    payload = single_scenario(**{field: value})
                    with self.assertRaisesRegex(StudioEconomicsError, "^Invalid studio economics assumptions$"):
                        evaluate_studio_economics(payload)

    def test_names_and_scenario_counts_are_bounded_unique_and_preserved(self):
        for name in (None, 1, "", " ", "x" * (MAX_NAME_CHARACTERS + 1), "line\nbreak", "bad\ud800",
                     "sk-" + "SYNTHETICKEY" * 4):
            value = single_scenario()
            value["scenarios"][0]["name"] = name
            with self.assertRaises(StudioEconomicsError):
                evaluate_studio_economics(value)
        duplicate = example_payload()
        duplicate["scenarios"][1]["name"] = duplicate["scenarios"][0]["name"]
        with self.assertRaises(StudioEconomicsError):
            evaluate_studio_economics(duplicate)
        many = single_scenario()
        first = many["scenarios"][0]
        many["scenarios"] = [{**deepcopy(first), "name": f"Scenario {index}"} for index in range(MAX_SCENARIOS + 1)]
        with self.assertRaises(StudioEconomicsError):
            evaluate_studio_economics(many)
        many["scenarios"].pop()
        many["scenarios"][0]["name"] = "\u00e9" * MAX_NAME_CHARACTERS
        many["scenarios"][1]["name"] = "  Hypothetical Second Scenario  "
        result = evaluate_studio_economics(many)
        self.assertEqual([item["name"] for item in many["scenarios"]], [item["name"] for item in result["scenarios"]])

    def test_safe_integer_boundaries_are_exact_and_calculation_overflow_is_refused(self):
        result = evaluate_studio_economics(single_scenario(
            fixed_cash_cost_minor=0, production_minutes=0, expected_units=0,
            unit_price_minor=MAX_MINOR_UNITS, per_unit_delivery_cash_cost_minor=0,
            variable_fee_basis_points=10_000))["scenarios"][0]
        self.assertEqual(MAX_MINOR_UNITS, result["calculations"]["variable_fee_per_unit_minor"])
        self.assertTrue(all(type(value) is int for value in result["calculations"].values()))
        overflows = [dict(unit_price_minor=MAX_MINOR_UNITS, expected_units=2),
                     dict(production_minutes=MAX_PRODUCTION_MINUTES, hourly_value_minor=MAX_MINOR_UNITS),
                     dict(fixed_cash_cost_minor=MAX_MINOR_UNITS),
                     dict(unit_price_minor=MAX_MINOR_UNITS, variable_fee_basis_points=10_000,
                          per_unit_delivery_cash_cost_minor=1)]
        for values in overflows:
            with self.subTest(fields=sorted(values)), self.assertRaisesRegex(
                    StudioEconomicsError, "^Studio economics calculation exceeds supported bounds$"):
                evaluate_studio_economics(single_scenario(**values))

    def test_exact_assumption_hash_and_independent_copies(self):
        payload = example_payload()
        original = deepcopy(payload)
        report = evaluate_studio_economics(payload)
        expected_hash = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(expected_hash, report["input_sha256"])
        self.assertEqual(original, payload)
        self.assertEqual(report, evaluate_studio_economics(json.loads(json.dumps(payload, sort_keys=True))))
        report["scenarios"][0]["assumptions"]["expected_units"] = 999
        report["methodology"]["exclusions"].clear()
        report["qualifications"]["spend_approved"] = True
        self.assertEqual(original, payload)
        fresh = evaluate_studio_economics(payload)
        self.assertEqual(10, fresh["scenarios"][0]["assumptions"]["expected_units"])
        self.assertTrue(fresh["methodology"]["exclusions"])
        self.assertIs(False, fresh["qualifications"]["spend_approved"])
        payload["scenarios"][0]["assumptions"]["expected_units"] += 1
        self.assertNotEqual(expected_hash, evaluate_studio_economics(payload)["input_sha256"])

    def test_local_load_is_read_only_closes_streams_and_matches_pure_evaluation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "hypothetical.json"
            raw = json.dumps(example_payload()).encode()
            path.write_bytes(raw)
            streams = []
            real_fdopen = os.fdopen
            def track(*args, **kwargs):
                stream = real_fdopen(*args, **kwargs)
                stream.read = Mock(wraps=stream.read)
                streams.append(stream)
                return stream
            with patch("jarvis.studio_economics.os.fdopen", side_effect=track), \
                    patch("socket.create_connection", side_effect=AssertionError("network forbidden")) as network, \
                    patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")) as request:
                report = load_studio_economics(path)
                self.assertEqual(evaluate_studio_economics(example_payload()), report)
            network.assert_not_called()
            request.assert_not_called()
            self.assertTrue(all(stream.closed for stream in streams))
            streams[0].read.assert_called_once_with(MAX_INPUT_BYTES + 1)
            self.assertEqual(raw, path.read_bytes())
            self.assertEqual([path], list(Path(temporary).iterdir()))
            self.assertNotIn(str(path), json.dumps(report))
            path.write_bytes(raw + b" " * (MAX_INPUT_BYTES - len(raw)))
            self.assertEqual(report, load_studio_economics(str(path)))

    def test_local_load_refuses_unsafe_paths_and_malformed_or_oversized_json_statically(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "private-input-name.json"
            invalid = [b"", b"[", b"\xff", b'{"schema":"one","schema":"two"}',
                       b'{"value":NaN}', b'{"value":Infinity}', b"x" * (MAX_INPUT_BYTES + 1)]
            for raw in invalid:
                path.write_bytes(raw)
                with self.assertRaisesRegex(StudioEconomicsError, "^Cannot load local studio economics input$"):
                    load_studio_economics(path)
            path.write_text(json.dumps(example_payload()))
            link = root / "link.json"
            link.symlink_to(path)
            directory_link = root / "linked-directory"
            directory_link.symlink_to(root, target_is_directory=True)
            fifo = root / "pipe"
            os.mkfifo(fifo)
            for source in (root / "missing.json", root, link, directory_link / path.name, fifo,
                           "https://example.invalid/assumptions.json", "file:///private/input.json", None):
                with self.subTest(source_type=type(source).__name__), self.assertRaisesRegex(
                        StudioEconomicsError, "^Cannot load local studio economics input$"):
                    load_studio_economics(source)
            path.write_text(json.dumps({**example_payload(), "actuals": {"sales": 10}}))
            with self.assertRaisesRegex(StudioEconomicsError, "^Invalid studio economics assumptions$"):
                load_studio_economics(path)

    def test_read_size_race_and_parse_failures_still_close_the_input_stream(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.json"
            real_fdopen = os.fdopen
            streams = []
            def track(*args, **kwargs):
                stream = real_fdopen(*args, **kwargs)
                stream.read = Mock(wraps=stream.read)
                streams.append(stream)
                return stream
            path.write_bytes(b"x" * (MAX_INPUT_BYTES + 1))
            with patch("jarvis.studio_economics.os.fdopen", side_effect=track), \
                    patch("jarvis.studio_economics.os.fstat", return_value=SimpleNamespace(st_mode=stat.S_IFREG, st_size=1)):
                with self.assertRaisesRegex(StudioEconomicsError, "^Cannot load local studio economics input$"):
                    load_studio_economics(path)
            self.assertTrue(streams[-1].closed)
            streams[-1].read.assert_called_once_with(MAX_INPUT_BYTES + 1)
            path.write_bytes(b'{"unclosed":')
            with patch("jarvis.studio_economics.os.fdopen", side_effect=track):
                with self.assertRaises(StudioEconomicsError):
                    load_studio_economics(path)
            self.assertTrue(streams[-1].closed)

    def test_failed_stream_construction_closes_the_open_descriptor(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.json"
            path.write_text(json.dumps(example_payload()))
            real_close = os.close
            with patch("jarvis.studio_economics.os.fdopen", side_effect=OSError("SYNTHETIC_PRIVATE_ERROR")), \
                    patch("jarvis.studio_economics.os.close", wraps=real_close) as close:
                with self.assertRaisesRegex(StudioEconomicsError, "^Cannot load local studio economics input$"):
                    load_studio_economics(path)
            close.assert_called_once()
            with self.assertRaises(OSError):
                os.fstat(close.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
