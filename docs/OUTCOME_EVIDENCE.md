# Learning What Works Best

Jarvis separates published best-practice guidance from local outcome evidence.

Every preventive control can accumulate trials in an append-only JSON Lines ledger. A trial
records the control identifier, boolean success, system, context, metric, timestamp, and
evidence reference. Failures remain in the record.

Controls are ranked using the lower bound of a 95% Wilson confidence interval rather than raw
success percentage. This prevents one perfect trial from outranking a well-tested control.
Evidence grades remain preliminary below 10 trials, limited from 10 through 29, and moderate
at 30 or more.

The ranking is transparent but not causal proof. Context differences, selection effects,
measurement quality, and correlated failures still require review. External standards remain
useful priors; local evidence shows whether a control is working in this particular ecosystem.
