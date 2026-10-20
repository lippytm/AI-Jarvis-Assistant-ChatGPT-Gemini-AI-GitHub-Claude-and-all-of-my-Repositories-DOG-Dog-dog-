# Studio economics: hypothetical production experiments

`studio-economics` evaluates the cash costs and production labor opportunity cost
of a small digital-content experiment. Each scenario contains supplied assumptions
and a hypothetical unit count. The command reports their arithmetic consequences,
including the whole-unit counts needed to cover the entered costs.

Every report has `status: hypothetical_scenarios_only` and
`qualifications.assumptions_status: provided_unverified_assumptions`. The input
does not authenticate its author or establish that the owner approved its values.
Version 1 has no measured-actuals input, sales ledger, demand model, tax calculation
or spending authorization.

The contract is implemented in [studio_economics.py](../src/jarvis/studio_economics.py),
with the command in [cli.py](../src/jarvis/cli.py) and offline regressions in
[test_studio_economics.py](../tests/test_studio_economics.py).

## Run the command

From an installed checkout:

```sh
jarvis studio-economics PATH --json
```

`PATH` is a regular local JSON file using the schema below. To evaluate the
checked-in [workforce-pilot example](../examples/studio-workforce-pilot/economics.json)
from the repository root:

```sh
jarvis studio-economics examples/studio-workforce-pilot/economics.json --json
```

For a source checkout with Python 3.11 or newer, use:

```sh
PYTHONPATH=src python -m jarvis studio-economics \
  examples/studio-workforce-pilot/economics.json --json
```

The command prints a JSON report to standard output. It reads the supplied file
without changing it, initializes no task ledger, and performs no provider,
network, account, publication or payment operation. It does not automatically
save a report or attach it to a production packet.

A valid calculation returns exit code `0`, including scenarios with negative
results or no finite break-even. Input or arithmetic-bound errors return exit
code `2` and a static `Jarvis error: ...` message on standard error; they do not
produce a partial economics report.

## Exact v1 input

The top-level object must contain exactly `schema`, `currency`, and `scenarios`.
`schema` must be `jarvis.studio-economics.v1`, and `currency` must be `USD`.
Each scenario must contain exactly `name` and `assumptions`; each assumptions
object must contain all seven fields shown here. Additional fields, including
`actuals`, `approved`, or account information, are rejected.

This single-scenario example uses illustrative assumptions:

```json
{
  "schema": "jarvis.studio-economics.v1",
  "currency": "USD",
  "scenarios": [
    {
      "name": "10 units",
      "assumptions": {
        "fixed_cash_cost_minor": 6000,
        "production_minutes": 240,
        "hourly_value_minor": 2000,
        "unit_price_minor": 900,
        "per_unit_delivery_cash_cost_minor": 50,
        "variable_fee_basis_points": 500,
        "expected_units": 10
      }
    }
  ]
}
```

All seven values must be JSON integers. Booleans, floats such as `900.0`, strings
such as `"900"`, negative numbers, and nonfinite values are invalid. Monetary
inputs are **USD cents**: `900` means $9.00, and `2000` in `hourly_value_minor`
means $20.00 per hour. The tool performs no currency conversion.

| Assumption field | Meaning | Accepted range |
|---|---|---|
| `fixed_cash_cost_minor` | One-time cash cost for this experiment, separate from the labor opportunity cost below | 0–9,007,199,254,740,991 cents |
| `production_minutes` | One-time production labor duration in whole minutes | 0–1,000,000 minutes |
| `hourly_value_minor` | Assumed value of one production hour, used to calculate opportunity cost | 0–9,007,199,254,740,991 cents/hour |
| `unit_price_minor` | Hypothetical gross amount per unit before modeled fees and delivery cash cost | 0–9,007,199,254,740,991 cents |
| `per_unit_delivery_cash_cost_minor` | Constant cash cost per modeled unit, excluding the percentage fee calculated separately | 0–9,007,199,254,740,991 cents |
| `variable_fee_basis_points` | Assumed percentage fee applied to the unit price; 100 basis points = 1%, and 500 = 5% | 0–10,000 basis points |
| `expected_units` | Hypothetical whole-unit count for this scenario | 0–1,000,000 units |

`expected_units` and the output prefix `expected_` label a calculation under a
supplied unit-count assumption. They are not a statistical expected value,
measured demand, a forecast, or evidence that units have been sold.

### Structural and file bounds

An input contains 1–16 scenarios. Each name must be a nonblank string of at most
128 characters. Exact duplicate names are rejected; accepted spelling, casing,
Unicode, surrounding spaces and scenario order are preserved. Names containing
ASCII control characters, unpaired Unicode surrogates or credentials recognized
by the existing sensitive-data checker are refused.

The file loader accepts at most 64 KiB (65,536 bytes) of UTF-8 JSON. It rejects
duplicate JSON object keys, malformed encoding or JSON, remote URLs, nonregular
files, and symlinks in the supplied path or its parent components. Its read is
bounded even if the file grows after its size is checked. Streams close on both
success and failure.

Every returned integer must remain within the inclusive signed range
−9,007,199,254,740,991 to 9,007,199,254,740,991. Input costs are nonnegative, but
calculated contribution and results may be negative. An individually valid input
can still be rejected when multiplication, addition or a calculated loss would
put a returned value outside this range. The implementation uses exact integer
arithmetic and rejects such results rather than returning rounded large numbers.

## Calculations and rounding

Each scenario describes one production experiment with one-time fixed costs and
constant per-unit price, delivery cost and percentage fee. No daily, monthly,
annual or recurring period is inferred. Scenarios are evaluated independently;
their results should not be added together as if the same production experiment
had happened several times.

Use the following symbols, with monetary values in cents:

| Symbol | Input |
|---|---|
| `F` | `fixed_cash_cost_minor` |
| `T` | `production_minutes` |
| `H` | `hourly_value_minor` |
| `P` | `unit_price_minor` |
| `D` | `per_unit_delivery_cash_cost_minor` |
| `B` | `variable_fee_basis_points` |
| `U` | `expected_units` |

`ceil` rounds upward to a whole integer. The model first computes:

```text
L = ceil(T × H / 60)          one-time labor opportunity cost
f = ceil(P × B / 10,000)      percentage fee per unit
v = D + f                    total variable cash cost per unit
c = P − v                    cash contribution per unit
```

The fee rounds upward **for each unit**, before multiplying by `U`. For example,
a hypothetical 0.01% fee on a one-cent unit rounds up to one cent per unit in this
model. It does not aggregate fractional fees across units or reproduce a
particular processor's billing rules. The labor calculation rounds upward once
per scenario after converting minutes into hours. There is no floating-point
rounding or intermediate dollar conversion.

Each scenario's `calculations` object contains these exact fields:

| Output field | Formula |
|---|---|
| `production_labor_opportunity_cost_minor` | `L` |
| `fixed_cost_including_labor_opportunity_cost_minor` | `F + L` |
| `variable_fee_per_unit_minor` | `f` |
| `variable_cash_cost_per_unit_minor` | `v` |
| `cash_contribution_per_unit_minor` | `c` |
| `expected_revenue_minor` | `U × P` |
| `expected_variable_cash_cost_minor` | `U × v` |
| `expected_total_cash_cost_minor` | `F + U × v` |
| `expected_cash_contribution_minor` | `U × c` |
| `expected_cash_result_after_fixed_cost_minor` | `U × c − F` |
| `expected_result_after_labor_opportunity_cost_minor` | `U × c − F − L` |

Cash contribution is the amount remaining after the modeled per-unit cash costs,
before fixed costs. The cash result then deducts the one-time fixed cash cost.
The last result additionally charges the assumed value of production time. That
labor amount is an opportunity-cost assumption, not a recorded wage payment or
cash expense. Keep its scope distinct from labor already included in entered
cash costs to avoid unintentionally counting the same burden twice.

### Whole-unit break-even

When `c > 0`, the report uses:

```text
cash_units            = ceil(F / c)
including_labor_units = ceil((F + L) / c)
status                = "finite"
```

Each count is the first whole-unit count at which its modeled result is
nonnegative. A finite threshold is a cost-recovery calculation, not a claim that
the units can or will be sold. It does not depend on `expected_units`, and can be
larger than the input's hypothetical unit count or its allowed 1,000,000-unit
input ceiling, provided the calculated threshold remains within the supported
integer range.

When `c <= 0`, the result is always:

```json
{
  "status": "no_finite_break_even",
  "cash_units": null,
  "including_labor_units": null
}
```

This is a conservative **volume-based recovery** rule. It also applies when
fixed cash and labor costs are zero: a zero-unit or zero-contribution arithmetic
result of zero is not reported as a finite recovery threshold. If contribution
is positive and the relevant fixed cost is zero, the corresponding finite
break-even count is `0`.

## The four workforce-pilot cases

The checked-in [economics.json](../examples/studio-workforce-pilot/economics.json)
contains four assistant-authored teaching scenarios: `No sales`, `10 units`,
`25 units`, and `50 units`. Their hypothetical unit counts are 0, 10, 25, and 50.
The name `No sales` describes a counterfactual scenario; it is not an observation
about the studio's actual sales.

All four use an illustrative $9 unit price, $60 fixed cash cost, 240 production
minutes valued at $20/hour, $0.50 per-unit delivery cost, and a 5% variable-fee
assumption. These are supplied teaching values, not approved prices or budgets,
published offers, actual provider terms, observed costs, or forecasts.

The calculated labor opportunity cost is $80.00. The assumed percentage fee is
$0.45 per unit, so variable cash cost is $0.95 and cash contribution is $8.05 per
unit. Fixed cash plus labor opportunity cost totals $140.00.

The table displays dollars for readability; the report returns integer cents.

| Hypothetical units | Revenue | Cash contribution before fixed costs | Cash result after fixed costs | Result after labor opportunity cost |
|---:|---:|---:|---:|---:|
| 0 (`No sales`) | $0.00 | $0.00 | −$60.00 | −$140.00 |
| 10 | $90.00 | $80.50 | $20.50 | −$59.50 |
| 25 | $225.00 | $201.25 | $141.25 | $61.25 |
| 50 | $450.00 | $402.50 | $342.50 | $262.50 |

All four share a cash break-even threshold of **8 units** and a threshold of
**18 units including labor opportunity cost**. The hypothetical 10-unit case
shows why the distinction matters: it covers entered cash costs, but leaves
$59.50 of the assumed production-time value unrecovered. The zero-unit case
still incurs the assumed $60 cash cost and $80 opportunity cost of producing the
edition.

A useful next observation would be which entered quantities need better evidence:
actual production duration, the intended delivery arrangement, applicable fees,
acquisition effort, or reader interest. Record observations separately; changing
an assumption file does not create or preserve an actuals ledger. The
[pilot experiment](../examples/studio-workforce-pilot/pilot-experiment.md) describes
the proposed reader and production work that remains separate from this calculation.

## Report structure and provenance

The report's top-level fields are:

| Field | Meaning |
|---|---|
| `schema` | `jarvis.studio-economics-report.v1` |
| `status` | Always `hypothetical_scenarios_only` |
| `currency`, `monetary_unit` | `USD` and `USD_cent` |
| `input_sha256` | SHA-256 of the validated canonical input described below |
| `qualifications` | Fixed declarations about assumptions and the absence of measured or verified outcomes |
| `methodology` | Period, rounding, cost basis and exclusions used by this version |
| `scenarios` | Ordered scenario objects, each containing `name`, `assumptions`, `calculations`, and `break_even` |

The qualification fields are fixed:

```json
{
  "assumptions_status": "provided_unverified_assumptions",
  "measured_actuals_included": false,
  "demand_verified": false,
  "rights_verified": false,
  "taxes_calculated": false,
  "spend_approved": false,
  "forecast_guaranteed": false,
  "provider_calls": 0
}
```

The hash covers the exact accepted schema, currency, scenario names, scenario
order and seven assumptions in each scenario. Canonicalization uses sorted object
keys, compact separators, unescaped Unicode and UTF-8, with no trailing newline:

```python
sha256(json.dumps(validated_input, sort_keys=True, separators=(",", ":"),
                  ensure_ascii=False).encode("utf-8")).hexdigest()
```

Formatting or object-key-order changes in the file leave this hash unchanged.
Changing an accepted value, a scenario name or scenario order changes it. It is
not the hash of the source file's bytes or the report's bytes. The loader adds no
source path to the report, and returned objects are independent copies.

`input_sha256` identifies supplied assumptions. It does not authenticate an
author, validate provider terms, prove an outcome, identify the executing code
revision, or verify the freshness of another brief or asset. Keep the report with
the relevant code revision and project evidence when comparing runs. Any binding
to a production packet or source revision must be recorded separately; this
calculator does not read or verify those dependencies.

## Cost and evidence exclusions

The report's methodology explicitly records the following limits:

- Taxes are not calculated. There is no tax-inclusive pricing, tax liability or
  after-tax result.
- Refunds, returns and chargebacks are not modeled.
- Fixed per-transaction fees are not calculated separately. If one transaction
  corresponds to one modeled unit, an assumed flat fee can be included in
  `per_unit_delivery_cash_cost_minor`. This model does not allocate transaction
  fees across multi-unit baskets.
- Customer acquisition cost is not calculated separately. An assumed fixed or
  per-unit amount can be included in the corresponding entered cash costs.
- Ongoing labor is not modeled. `production_minutes` covers the one-time
  production opportunity cost, without a recurring support or revision schedule.
- Demand, source rights, author identity and account permissions are not verified.
- No actual sales, payouts or commissions are recorded. No spending or release
  action is approved.

Only entered cost categories affect the arithmetic. A positive calculated result
does not establish a complete business margin, finished production quality,
release readiness, demand, or forecast certainty.

## Developer reproduction and errors

The module uses the Python standard library and exposes two functions:

```python
from pathlib import Path
from jarvis.studio_economics import evaluate_studio_economics, load_studio_economics

report = evaluate_studio_economics(payload)  # Validated in-memory dict -> report
report = load_studio_economics(Path("examples/studio-workforce-pilot/economics.json"))
```

`evaluate_studio_economics` performs no file or network I/O. The loader reads one
local input and returns the same evaluation; it does not return an unevaluated
payload. Neither function mutates the supplied assumptions or persists a result.
The checked-in example can be reproduced with the command above, and the focused
regressions can be run from the repository root:

```sh
PYTHONPATH=src python -m unittest discover -s tests -p 'test_studio_economics.py' -v
```

`StudioEconomicsError` is a `ValueError` subclass with static messages:

| Message | Meaning |
|---|---|
| `Invalid studio economics assumptions` | Unsupported schema/currency, invalid structure, extra or missing fields, invalid names, or input numbers outside their accepted type/range |
| `Studio economics calculation exceeds supported bounds` | A valid set of individual inputs produces a result outside the supported integer range |
| `Cannot load local studio economics input` | Unreadable or unsafe path, oversized input, malformed UTF-8/JSON, or duplicate JSON keys |

The CLI prefixes these messages with `Jarvis error: `. Validation messages do not
quote submitted values, file paths or raw operating-system errors. The tests cover
the example arithmetic, upward rounding, first-whole-unit break-even, nonpositive
contribution, zero-unit losses, overflow rejection, strict schemas, hash identity,
independent copies, bounded reads, unsafe paths and input closure on failures.
