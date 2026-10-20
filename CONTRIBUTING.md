# Contributing

1. Create a focused branch.
2. Never commit credentials or customer data.
3. Add tests for behavior changes.
4. Run `python -m unittest discover -s tests -v`.
5. Open a pull request explaining purpose, risk, testing, and rollback.

Providers and connectors must preserve task IDs and provenance and must not silently fall back to a different paid provider.
