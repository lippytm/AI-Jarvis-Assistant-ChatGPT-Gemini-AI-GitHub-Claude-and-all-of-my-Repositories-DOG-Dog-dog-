# AI Jarvis Assistant — Control Tower

An auditable, provider-neutral assistant that coordinates work across OpenAI, Gemini, Claude, GitHub, and future business systems without storing credentials in the repository.

> Status: **v0.1 foundation**. The CLI, task ledger, provider routing, mock mode, health checks, and tests are working. External providers require your own API keys and remain disabled until configured.

## What works now

- One task contract shared by every AI provider
- OpenAI, ChatGPT, Anthropic Claude, Google Gemini, Gemini-Jarvis, Perplexity, and offline mock adapters
- SQLite task, event, and response ledger with provenance
- Correlation IDs, timestamps, provider/model records, and response hashes
- Connector health checks that never reveal secrets
- Command-line interface with JSON output for automations
- GitHub Actions tests and dependency review
- Extension contract for GitHub, Hostinger, Slack, Zapier, and other connectors

## Architecture

```text
User / Automation -> Jarvis CLI -> Control Tower -> Provider Router
                                      |
                               Provenance ledger
```

Jarvis coordinates providers; it does not make them secretly communicate. Every cross-system handoff is an explicit, logged task. Human approval remains required for financial, publishing, credential, deletion, and production-deployment actions.

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .
jarvis health
jarvis ask "Create a three-step business launch checklist" --provider mock
jarvis history
jarvis workflows
jarvis run multi_ai_business_review "Evaluate my new product idea" --allow-external
```

The default is `mock`, so the project runs without paid API calls. Set environment variables described in [`.env.example`](.env.example) to enable a real provider. The CLI intentionally does not automatically load `.env`; a shell, secret manager, or deployment platform should inject secrets.

```bash
export JARVIS_DEFAULT_PROVIDER=openai
export OPENAI_API_KEY=replace-me
jarvis ask "Summarize this project" --provider openai
```

Never commit `.env`, tokens, passwords, OAuth refresh tokens, or customer data.

## Commands

```bash
jarvis health [--json]
jarvis ask "TASK" [--provider mock|openai|anthropic|gemini] [--system "..."] [--json]
jarvis history [--limit 20] [--json]
jarvis show TASK_ID [--json]
jarvis workflows [--json]
jarvis run WORKFLOW "INPUT" [--allow-external] [--json]
jarvis plan WORKFLOW "INPUT" [--json]
jarvis bundle RUN_ID [--json]
jarvis verify-bundle PATH [--json]
jarvis doctor [--json]
jarvis intake gemini-ai-jarvis PATH [--title TITLE] [--json]
jarvis intakes [--json]
jarvis patrol [--owner lippytm] [--json]
jarvis improve data/patrol/latest.json [--json]
jarvis assess-problem problem.json [--json]
jarvis assess-viability design.json [--json]
```

## Automated workflows

Workflow definitions live in `workflows/*.json`. External AI calls are skipped unless
`--allow-external` is supplied, preventing accidental paid requests. Handoff steps create
drafts in `data/outbox`; they do not silently post, publish, or message anyone.

- `multi_ai_business_review`: Perplexity research → Gemini Jarvis design → Claude review → ChatGPT synthesis → ChatGPT Business draft handoff.
- `repository_fleet_review`: GitHub inventory of accessible repositories → ChatGPT portfolio review → GitHub draft handoff.
- `prompt_11_product_factory`: market research → product genome → independent QA challenge → master build → owner approval → Business handoff.
- `jarvis_problem_council`: evidence research → scenarios → adversarial review → synthesis → blind-spot challenge → verification → owner approval.

Identical workflow inputs reuse their prior completed report so retries do not accidentally
repeat paid calls. Supply `--force` only when a deliberate fresh run is required. Approval
steps create reviewable records; approving a record does not automatically publish or spend.

Every workflow has an external-call budget (`JARVIS_MAX_EXTERNAL_CALLS`, default 6), a
no-cost planning mode, high-confidence credential detection, redacted persisted reports,
and per-step execution timing. See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) before enabling
live provider calls.

Completed runs can be packaged into provenance-preserving `.jarvis.zip` transfer bundles.
Each bundle carries a manifest and SHA-256 digest for every artifact, allowing another
workstation to reject tampering or incomplete transfers. See [`docs/ROUND_TRIP.md`](docs/ROUND_TRIP.md).

`jarvis doctor` performs a non-billable local readiness audit. GitHub also runs a weekly
credential-free audit that validates workflows, compiles the package, runs tests, and stores
the reports for 30 days. See the [capability matrix](docs/CAPABILITIES.md) and
[threat model](docs/THREAT_MODEL.md).

The always-on layer runs a bounded, read-only repository patrol every day after this
branch is merged into the default branch. It records health findings and improvement
proposals as artifacts, with circuit breakers and approval required for every repository
change. See [always-on operations](docs/ALWAYS_ON.md), the [continuous improvement contract](docs/CONTINUOUS_IMPROVEMENT.md), the [Problem Council](docs/PROBLEM_COUNCIL.md), [universal problem intake](docs/PROBLEM_INTAKE.md), and [preventive diagnostics](docs/PREVENTIVE_DIAGNOSTICS.md).

The intake bridge captures UTF-8 Markdown, text, or JSON exported from Gemini Jarvis, Claude,
or another workstation. It records provenance, detects common credentials, stores a redacted
copy, and creates a structured ChatGPT Business handoff. Follow the
[Gemini migration procedure](docs/GEMINI_MIGRATION.md).

```bash
jarvis validate-workflows --json
jarvis approvals --status pending
jarvis approve APPROVAL_ID
```

`ChatGPT Business` is a workspace product, not a general automation endpoint. This project
uses the OpenAI API for automated model calls and creates explicit handoff artifacts for the
Business workspace. That boundary prevents a misleading or fragile integration claim.

Future connectors implement `Connector` and declare read, draft, write, or destructive risk. Writes need explicit approval; destructive actions are disabled in v0.1. See [`docs/CONNECTORS.md`](docs/CONNECTORS.md) and [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m jarvis health --json
```

## Mission and naming

The mission is to build useful Jarvis connections across the places where Charles creates and operates businesses: ChatGPT, Gemini, Claude, GitHub, Hostinger, and related repositories. `Jarvis/DOG` is the canonical project identity; `Dog` and `dog` may be used as stylistic variants.

## License

CC0-1.0, matching the repository's existing license choice. Review it with qualified counsel before distributing a commercial product or accepting outside contributions.
