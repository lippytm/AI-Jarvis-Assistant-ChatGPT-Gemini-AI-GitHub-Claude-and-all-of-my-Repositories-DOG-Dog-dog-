# Preventive Diagnostics and Viability Design

Jarvis evaluates designs before implementation so foreseeable failures become documented
findings instead of production incidents.

## Ten preventive dimensions

1. Clear outcome and non-goals
2. Current-state evidence
3. Accountable owner and approval authority
4. Upstream and downstream dependencies
5. Logs, metrics, alerts, and provenance
6. Deterministic tests and baseline
7. Reversible experiment design
8. Verified rollback procedure
9. Time, API, compute, and financial cost caps
10. Security, privacy, secrets, and abuse controls

Each dimension receives 0 (missing), 1 (partial), or 2 (documented). Unresolved conflicts
apply an additional penalty and block implementation. A score never proves safety; it is a
readiness signal.

## Gates

- **Blocked:** a high-severity prevention control or conflict is unresolved.
- **Revise:** no high-severity block remains, but readiness is below 80.
- **Sandbox ready:** readiness is at least 80 and work may proceed only to an isolated,
  reversible experiment with monitoring.

## Pre-mortem questions

Before building, assume the project failed and ask: Which dependency changed? Which owner was
missing? Which metric stayed invisible? Which permission was excessive? Which cost escaped its
limit? Which recovery procedure was never tested? Which stakeholder was harmed? Which
assumption was treated as fact?

Preventive design cannot solve problems before they exist in a literal sense. It can make
failure modes visible, testable, reversible, and cheaper before production exposure.
