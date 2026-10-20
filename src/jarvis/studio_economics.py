"""Bounded, local studio unit economics from hypothetical assumptions only."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

from .safety import find_sensitive


INPUT_SCHEMA = "jarvis.studio-economics.v1"
REPORT_SCHEMA = "jarvis.studio-economics-report.v1"
MAX_INPUT_BYTES = 64 * 1024
MAX_SCENARIOS = 16
MAX_NAME_CHARACTERS = 128
MAX_MINOR_UNITS = (1 << 53) - 1
MAX_PRODUCTION_MINUTES = 1_000_000
MAX_EXPECTED_UNITS = 1_000_000
ASSUMPTION_FIELDS = frozenset({
    "fixed_cash_cost_minor", "production_minutes", "hourly_value_minor",
    "unit_price_minor", "per_unit_delivery_cash_cost_minor",
    "variable_fee_basis_points", "expected_units",
})


class StudioEconomicsError(ValueError):
    """A static validation, arithmetic-bound or local-input error."""


def _invalid() -> StudioEconomicsError:
    return StudioEconomicsError("Invalid studio economics assumptions")


def _object(value: Any, fields: set[str] | frozenset[str]) -> dict[str, Any]:
    if type(value) is not dict or len(value) != len(fields) or set(value) != fields:
        raise _invalid()
    return value


def _integer(value: Any, maximum: int) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise _invalid()
    return value


def _name(value: Any) -> str:
    if (type(value) is not str or not value.strip() or len(value) > MAX_NAME_CHARACTERS
            or any(ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF for char in value)
            or find_sensitive(value)):
        raise _invalid()
    return value


def _assumptions(value: Any) -> dict[str, int]:
    value = _object(value, ASSUMPTION_FIELDS)
    bounds = {"production_minutes": MAX_PRODUCTION_MINUTES,
              "expected_units": MAX_EXPECTED_UNITS, "variable_fee_basis_points": 10_000}
    return {field: _integer(value[field], bounds.get(field, MAX_MINOR_UNITS))
            for field in sorted(ASSUMPTION_FIELDS)}


def _bounded_result(value: int) -> int:
    # Keep every returned integer exact in common JSON consumers as well as Python.
    if not -MAX_MINOR_UNITS <= value <= MAX_MINOR_UNITS:
        raise StudioEconomicsError("Studio economics calculation exceeds supported bounds")
    return value


def _ceil_div(numerator: int, denominator: int) -> int:
    return (numerator + denominator - 1) // denominator


def _evaluate_scenario(name: str, assumptions: dict[str, int]) -> dict[str, Any]:
    fixed = assumptions["fixed_cash_cost_minor"]
    units = assumptions["expected_units"]
    price = assumptions["unit_price_minor"]
    labor = _bounded_result(_ceil_div(
        assumptions["production_minutes"] * assumptions["hourly_value_minor"], 60))
    fee = _bounded_result(_ceil_div(price * assumptions["variable_fee_basis_points"], 10_000))
    variable = _bounded_result(assumptions["per_unit_delivery_cash_cost_minor"] + fee)
    contribution = _bounded_result(price - variable)
    fixed_with_labor = _bounded_result(fixed + labor)
    revenue = _bounded_result(price * units)
    variable_total = _bounded_result(variable * units)
    total_cash_cost = _bounded_result(fixed + variable_total)
    contribution_total = _bounded_result(contribution * units)
    cash_result = _bounded_result(contribution_total - fixed)
    result_with_labor = _bounded_result(cash_result - labor)
    if contribution > 0:
        break_even = {"status": "finite",
                      "cash_units": _bounded_result(_ceil_div(fixed, contribution)),
                      "including_labor_units": _bounded_result(_ceil_div(fixed_with_labor, contribution))}
    else:
        # Do not report volume-based recovery from a zero or negative contribution,
        # even if a zero-unit/zero-fixed-cost arithmetic result happens to be zero.
        break_even = {"status": "no_finite_break_even", "cash_units": None,
                      "including_labor_units": None}
    return {
        "name": name, "assumptions": assumptions,
        "calculations": {
            "production_labor_opportunity_cost_minor": labor,
            "fixed_cost_including_labor_opportunity_cost_minor": fixed_with_labor,
            "variable_fee_per_unit_minor": fee,
            "variable_cash_cost_per_unit_minor": variable,
            "cash_contribution_per_unit_minor": contribution,
            "expected_revenue_minor": revenue,
            "expected_variable_cash_cost_minor": variable_total,
            "expected_total_cash_cost_minor": total_cash_cost,
            "expected_cash_contribution_minor": contribution_total,
            "expected_cash_result_after_fixed_cost_minor": cash_result,
            "expected_result_after_labor_opportunity_cost_minor": result_with_labor,
        },
        "break_even": break_even,
    }


def evaluate_studio_economics(payload: dict) -> dict:
    """Evaluate 1–16 named assumptions; no actuals, writes, providers or accounts.

    Input schema: ``jarvis.studio-economics.v1``, currency: ``USD``, scenarios:
    ``[{name, assumptions: {fixed_cash_cost_minor, production_minutes,
    hourly_value_minor, unit_price_minor, per_unit_delivery_cash_cost_minor,
    variable_fee_basis_points, expected_units}}]``. No additional fields are
    accepted. Monetary inputs are nonnegative integer USD cents; calculated
    contribution and results may be negative. Fees round up per unit, one-time
    labor opportunity cost rounds up once, and break-even rounds up whole units.
    """
    payload = _object(payload, {"schema", "currency", "scenarios"})
    if payload["schema"] != INPUT_SCHEMA or payload["currency"] != "USD":
        raise _invalid()
    scenarios = payload["scenarios"]
    if type(scenarios) is not list or not 1 <= len(scenarios) <= MAX_SCENARIOS:
        raise _invalid()
    checked = []
    seen = set()
    for scenario in scenarios:
        scenario = _object(scenario, {"name", "assumptions"})
        name = _name(scenario["name"])
        if name in seen:
            raise _invalid()
        seen.add(name)
        checked.append({"name": name, "assumptions": _assumptions(scenario["assumptions"])})
    validated_input = {"schema": INPUT_SCHEMA, "currency": "USD", "scenarios": checked}
    encoded = json.dumps(validated_input, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "schema": REPORT_SCHEMA, "status": "hypothetical_scenarios_only",
        "currency": "USD", "monetary_unit": "USD_cent",
        "input_sha256": sha256(encoded).hexdigest(),
        "qualifications": {
            "assumptions_status": "provided_unverified_assumptions",
            "measured_actuals_included": False, "demand_verified": False,
            "rights_verified": False, "taxes_calculated": False,
            "spend_approved": False, "forecast_guaranteed": False, "provider_calls": 0,
        },
        "methodology": {
            "scenario_period": "one_production_experiment_no_recurring_period_assumed",
            "fee_rounding": "up_to_whole_minor_unit_per_unit",
            "labor_rounding": "up_to_whole_minor_unit_once_per_scenario",
            "break_even_rounding": "up_to_whole_unit",
            "nonpositive_contribution": "no_finite_break_even_even_with_zero_fixed_cost",
            "labor_basis": "one_time_production_opportunity_cost_not_cash_payment",
            "price_and_fee_basis": "provided_assumptions_not_verified_prices_or_provider_terms",
            "exclusions": [
                "Taxes are not calculated.",
                "Refunds, returns and chargebacks are not modeled.",
                "Fixed per-transaction fees are not calculated separately; include any assumed amount in per_unit_delivery_cash_cost_minor.",
                "Customer acquisition cost is not calculated separately; include any assumed amount in declared cash costs.",
                "Ongoing labor is not modeled; production_minutes covers one-time production only.",
                "Demand and rights are not verified.",
                "No actual sales, payouts or commissions are recorded, and no spending is authorized.",
            ],
        },
        "scenarios": [_evaluate_scenario(item["name"], item["assumptions"]) for item in checked],
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _invalid()
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise _invalid()


def load_studio_economics(path: Path | str) -> dict:
    """Read a bounded regular local UTF-8 JSON input and return its evaluation.

    URL inputs and symlink path components are refused. No source path is retained
    in the report. All input streams close before parsing or evaluation returns.
    """
    try:
        supplied = os.fspath(path)
        if type(supplied) is not str or re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", supplied):
            raise _invalid()
        local = Path(supplied).absolute()
        for component in (local, *local.parents):
            if stat.S_ISLNK(component.lstat().st_mode):
                raise _invalid()
        if not stat.S_ISREG(local.lstat().st_mode):
            raise _invalid()
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(local, flags)
        try:
            stream = os.fdopen(descriptor, "rb")
        except Exception:
            os.close(descriptor)
            raise
        with stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_INPUT_BYTES:
                raise _invalid()
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise _invalid()
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                             parse_constant=_reject_constant)
    except (OSError, TypeError, ValueError, RecursionError):
        raise StudioEconomicsError("Cannot load local studio economics input") from None
    return evaluate_studio_economics(payload)
