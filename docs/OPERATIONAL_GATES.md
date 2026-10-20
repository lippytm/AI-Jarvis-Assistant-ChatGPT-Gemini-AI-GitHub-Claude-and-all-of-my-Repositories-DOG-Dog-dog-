# Workflow execution and readiness gates

The October 20, 2026 maintenance update makes the existing runner's status and
command exit codes usable as automation gates.

## Run outcomes

| Report status | Meaning | CLI exit |
| --- | --- | --- |
| `completed` | Every declared step completed or produced its local draft. | 0 |
| `pending_approval` | A request was recorded; all later steps were stopped. | 1 |
| `blocked` | A required external provider was not enabled; later steps were stopped. | 1 |
| `failed` | A step raised an error; later steps were stopped. | 1 |

Each report identifies the workflow definition hash and lists `not_run_steps`.
Step failures retain the error class without copying exception bodies, provider
responses, or credentials into the failure description. Validation failures and
other invalid command inputs also exit nonzero.

An approval record is a request for review. This runner does not implement an
authenticated approval-to-resume endpoint. Editing an approval JSON file or using
the legacy local `approve` command does not cause a stopped run to continue.

## Repeat runs

The run identity includes the workflow name, normalized definition hash, input,
and explicit external/sensitive-input modes. Completed runs and pending approval
requests can be reused; failed and blocked runs can be retried. Changing the
definition or execution mode produces a new identity. `--force` still requests a
new run, and can therefore create a new local approval request or draft.

## Validation and readiness

`validate-workflows` rejects an empty catalog, malformed definitions, and workflow
filenames that cannot be loaded. Names use letters, numbers, underscores and
hyphens. Invalid validation returns exit 1 with a structured report.

`doctor` returns exit 0 only for `ready_local`. It reports configured external
providers separately, and keeps `live_workflows_ready` false because it makes no
network call. Configured credentials are not evidence of a successful connection.
A live workflow requires a separately retained execution receipt.

In GitHub Actions, use an explicit Bash shell for pipelines so `pipefail` preserves
the command's failure through `tee`. A successful artifact upload alone does not
establish a successful audit; inspect required step outcomes and report hashes.

## Local verification

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_operational_gates.py' -v
PYTHONPATH=src python3 -m jarvis validate-workflows --json
PYTHONPATH=src python3 -m jarvis doctor --json
```

These checks do not publish products, invoke paid providers, or start a background
service. The companion public GitHub audit is a separately bounded workflow.
