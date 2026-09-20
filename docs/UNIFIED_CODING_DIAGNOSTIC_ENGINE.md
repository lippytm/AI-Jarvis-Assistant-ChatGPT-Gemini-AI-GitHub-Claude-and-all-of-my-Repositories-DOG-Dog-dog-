# Unified Coding Engine / Diagnostic Engine

Status: architecture and controlled-pilot specification  
Owner: Charles Earl Lipshay  
Date: 2026-09-20

## Outcome

Create one governed workflow that can route work among Codex, GitHub Copilot, additional model providers, repository tools, CI, security scanners, and runtime observability. The systems remain technically separate. Unification happens through contracts, capability routing, shared instructions, evidence, and approval controls.

## Architecture

### 1. Intake and portfolio context

AI Jarvis receives a goal, identifies the repository, checks its lifecycle and risk class, and creates a bounded work envelope.

### 2. Coding Engine

The router selects a suitable coding provider:

- Codex for agentic repository work, diagnostics, implementation, tests, and review.
- GitHub Copilot for repository-local development workflows and pull-request preparation.
- Additional providers for independent critique or specialist analysis.
- Local tools for mechanical transformations and deterministic checks.

A provider receives only the minimum repository context and tools needed for that task.

### 3. Diagnostic Engine

The engine runs an evidence ladder:

1. reproduce the issue;
2. capture the smallest safe diagnostic evidence;
3. form ranked hypotheses;
4. run deterministic tests that distinguish the hypotheses;
5. propose a minimal patch;
6. add a regression test when practical;
7. rerun compilation, tests, lint, type checks, dependency audits, and security checks;
8. obtain an independent review for high-risk changes;
9. generate a receipt and rollback plan.

### 4. Risk and approval gate

The engine may prepare branches, patches, tests, documentation, reports, and draft pull requests. Merges, production deployments, publications, spending, external messages, credential operations, security-control changes, private-data disclosures, and destructive actions require explicit approval.

### 5. Evidence and memory

MemPalace-compatible records retain only approved metadata: bundle ID, provider, repository, branch, commit, hashes, checks, findings, decisions, and rollback. Secrets and raw private content are excluded.

## Shared contracts

### Work envelope

Required fields:

- `bundle_id`
- `repository`
- `goal`
- `scope`
- `risk_class`
- `allowed_tools`
- `prohibited_actions`
- `acceptance_tests`
- `approval_state`
- `input_hash`

### Diagnostic receipt

Required fields:

- `bundle_id`
- `provider`
- `repository`
- `branch`
- `commit`
- `files_changed`
- `reproduction`
- `findings`
- `checks_run`
- `check_results`
- `result_hash`
- `limitations`
- `rollback`
- `approval_state`

## Diagnostic modes

| Mode | Purpose | Output |
| --- | --- | --- |
| Triage | Classify a reported problem without changing code | Ranked hypotheses and next tests |
| Reproduce | Create a deterministic failure | Reproduction command/test and evidence |
| Repair | Propose minimal fix | Patch, regression test, receipt |
| Review | Evaluate an existing change | Findings with severity and evidence |
| Hardening | Reduce attack/failure surface | Threat model and reviewable recommendations |
| Portfolio health | Compare repository readiness | Public/private-safe scorecard |

## Tool adapters

Adapters must declare:

- identity and version;
- supported operations;
- input and output schemas;
- permission requirements;
- data-retention behavior;
- network requirements;
- timeout and cost limits;
- receipt support;
- rollback support;
- connection-verification state.

An adapter is not considered live until a harmless minimum-permission round trip passes.

## Pilot sequence

1. Review the shared instructions and provider registry.
2. Choose one low-risk public repository.
3. Create a documentation-only work envelope.
4. Run it separately through Codex and Copilot.
5. Compare receipts and deterministic checks.
6. Record disagreements and human review.
7. Repeat with a small tested code change.
8. Expand to additional tools only after success criteria are met.

## Success metrics

- percentage of tasks with verified receipts;
- first-pass test success;
- escaped-defect rate;
- review rework;
- false-positive diagnostic rate;
- mean time to reproduce;
- mean time to verified repair;
- rollback readiness;
- unauthorized-action count;
- cost and latency by provider.

## Non-goals

- claiming the models share internal reasoning or memory;
- giving every provider access to every repository;
- using majority model opinion as proof;
- autonomous merge or deployment;
- exposing credentials or private business data;
- promising a bug-free or impregnable system.

## Current implementation surfaces

- `AGENTS.md` provides the Codex-side Jarvis operating contract.
- `.github/copilot-instructions.md` provides the Copilot-side contract.
- `.jarvis/providers/provider-registry.yaml` declares providers and routing.
- `.jarvis/providers/github-copilot.yaml` defines the first provider bridge.
- The next implementation is a shared JSON Schema for work envelopes and diagnostic receipts, followed by one harmless round-trip test.
