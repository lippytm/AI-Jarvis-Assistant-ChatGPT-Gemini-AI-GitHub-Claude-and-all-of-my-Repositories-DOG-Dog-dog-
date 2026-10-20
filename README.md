# AI Jarvis Assistant — Control Tower

An auditable, provider-neutral assistant that coordinates work across OpenAI, Gemini, Claude, GitHub, and future business systems without storing credentials in the repository.

> Status: **operational pilot**. The CLI, local task ledger, workflow gates, provider routing, mock mode, and public GitHub audit are tested. External AI providers require an API key, an explicitly selected compatible model, and the applicable execution opt-in. Configuration checks do not establish live account readiness.

## What works now

- One task contract shared by every AI provider
- OpenAI, ChatGPT, Anthropic Claude, Google Gemini, Gemini-Jarvis, Perplexity, and offline mock adapters
- SQLite task, event, and response ledger with provenance
- Correlation IDs, timestamps, provider/model records, and response hashes
- Connector health checks that never reveal secrets
- Command-line interface with JSON output for automations
- One versioned Prompt #11 operating profile across all eight catalog workflows and the local Node task planner
- Structured creative production packets with real local source drafts, dependency checks, and verified handoff files
- Hypothetical production economics that separate cash costs from the value of production time
- GitHub Actions tests and dependency review
- Extension contract for GitHub, Hostinger, Slack, Zapier, and other connectors

## Architecture

The CLI sends each task through the Control Tower to the selected provider. The
local provenance ledger records task, response and event evidence. The workflow
runner adds ordered steps, shared operating guidance and explicit stop conditions.

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
jarvis plan multi_ai_business_review "Evaluate my new product idea" --json
```

The default is `mock`, so this quick start makes no paid API calls. To enable a
real provider, inject the API key and an explicit model ID described in
[`.env.example`](.env.example). The CLI intentionally does not automatically load
`.env`; a shell, secret manager, or deployment platform should inject secrets.
The following example is a live API request after its placeholders are replaced:

```bash
export JARVIS_DEFAULT_PROVIDER=openai
export OPENAI_API_KEY=replace-me
export OPENAI_MODEL=replace-with-a-model-supported-by-your-account-and-endpoint
jarvis ask "Summarize this project" --provider openai
```

Never commit `.env`, tokens, passwords, OAuth refresh tokens, or customer data.

Model IDs have no fallback. Select a model available to your account and the
adapter's endpoint: Python uses OpenAI Responses, Anthropic Messages, Google
Gemini generateContent, or Perplexity Chat Completions. The Node pilot uses
OpenAI Chat Completions for its OpenAI adapter; see its
[runtime configuration](runtime/README.md). A local health check verifies
configuration presence, not model availability or successful authentication.

Python provider requests cap output at 2,000 tokens and responses at 1 MiB, use
the configured request timeout, and reject redirects. Provider errors omit
upstream response bodies. These request bounds do not implement an aggregate
spending budget or guarantee that a selected model supports every request field.
Only a completed, nonempty native text response advances a workflow. Malformed,
blocked, refused, truncated or unfinished responses fail the step, stop downstream
handoffs and remain outside the successful-run cache. Invalid credential and
request-header errors are reported without their secret values.

The Perplexity adapter currently uses its legacy synchronous Chat Completions
shape. Perplexity's [migration notice](https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar/overview)
states that Sonar support ended on September 27, 2026, with synchronous calls
being reformulated as Agent API requests. This adapter's live compatibility is
unverified; a native Agent API migration is separate work before production use.

## Commands

```bash
jarvis health [--json]
jarvis ask "TASK" [--provider mock|openai|anthropic|gemini] [--system "..."] [--json]
jarvis history [--limit 20] [--json]
jarvis show TASK_ID [--json]
jarvis workflows [--json]
jarvis run WORKFLOW "INPUT" [--business-context PATH] [--allow-external] [--json]
jarvis plan WORKFLOW "INPUT" [--business-context PATH] [--json]
jarvis business-context PATH [--json]
jarvis studio-plan BRIEF --output FRESH_DIRECTORY [--json]
jarvis verify-studio-plan DIRECTORY [--json]
jarvis studio-economics ASSUMPTIONS [--json]
jarvis bundle RUN_ID [--json]
jarvis verify-bundle PATH [--json]
jarvis doctor [--json]
jarvis intake gemini-ai-jarvis PATH [--title TITLE] [--json]
jarvis intakes [--json]
jarvis patrol [--owner lippytm] [--json]
jarvis improve data/patrol/latest.json [--json]
jarvis assess-problem problem.json [--json]
jarvis assess-viability design.json [--json]
jarvis recommend-controls [--domain ai] [--domain software] [--json]
jarvis rank-outcomes outcomes.jsonl [--json]
```

## Automated workflows

Workflow definitions live in `workflows/*.json`. A run stops at its first external
AI step unless `--allow-external` is supplied; downstream steps remain unexecuted.
Handoff steps create drafts in `data/outbox` and require a separate, authorized
delivery to reach another system.

All eight catalog entries resolve the fixed Prompt #11 operating profile
`P-011-E6C-001`, revision `repository-1`. Each executed AI step receives the shared
guidance followed by its existing role. Plans, reports and validation retain the
profile's exact SHA-256 hash, and the run cache includes that identity. Missing
or invalid coverage fails validation. Profile resolution is recorded separately
from execution; it is not evidence that a model followed the guidance or that a
service was deployed. See [profile provenance and coverage](docs/PROMPT11_WORKFLOW_PROFILE.md).

An optional local business record can supply the same allowed company facts to
every executed AI step. The projector includes the business name, support email,
formation date, exact funding routes and qualified prior site decisions. It
excludes tax identifiers and all other private administration fields. Plans and
reports retain the sanitized pack's identity and hash; changes to those facts
invalidate the completed-run cache. The source record stays outside the repository.

```bash
jarvis plan unified_life_business_creation "Prepare a business review" \
  --business-context /private/owner-business-context.json --json
```

This plan makes no provider calls. The facts are task data and grant no account
access or approval. A separate `jarvis business-context PATH --json` command
exports the same safe pack for manual reuse in another authorized workspace.
See [business context and privacy boundaries](docs/BUSINESS_CONTEXT.md).

Examples from the catalog:

- `multi_ai_business_review`: Perplexity research → Gemini Jarvis design → Claude review → ChatGPT synthesis → ChatGPT Business draft handoff.
- `repository_fleet_review`: GitHub inventory of accessible repositories → ChatGPT portfolio review → GitHub draft handoff.
- `prompt_11_product_factory`: market research → product genome → independent QA challenge → master build → owner approval → Business handoff.
- `jarvis_problem_council`: evidence research → scenarios → adversarial review → synthesis → blind-spot challenge → verification → owner approval.
- `creative_studio_package`: local production templates → local review handoff → owner review; zero AI or publishing calls.

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

`jarvis doctor` performs a non-billable local readiness audit. The GitHub audit is
enabled on main and scheduled daily at 15:17 UTC, as well as on relevant pushes
and pull requests. Each bounded run tests the package, validates workflow and
Prompt #11 coverage, checks local readiness, and reads public repository metadata
to create health findings and improvement proposals. It retains hashed evidence
artifacts for 30 days. It makes no AI provider calls and is not a continuously
running worker or shared memory service. See the
[verified operational scope](docs/OPERATIONAL_PILOT.md),
[capability matrix](docs/CAPABILITIES.md) and [threat model](docs/THREAT_MODEL.md).

Repository changes remain subject to the operating contract and approval policy.
See [scheduled operations](docs/ALWAYS_ON.md), the [continuous improvement contract](docs/CONTINUOUS_IMPROVEMENT.md), the [Problem Council](docs/PROBLEM_COUNCIL.md), [universal problem intake](docs/PROBLEM_INTAKE.md), [preventive diagnostics](docs/PREVENTIVE_DIAGNOSTICS.md), the [prevention library](docs/PREVENTION_LIBRARY.md), and [outcome evidence](docs/OUTCOME_EVIDENCE.md).

The intake bridge captures UTF-8 Markdown, text, or JSON exported from Gemini Jarvis, Claude,
or another workstation. It records provenance, detects common credentials, stores a redacted
copy, and creates a structured ChatGPT Business handoff. Follow the
[Gemini migration procedure](docs/GEMINI_MIGRATION.md).

## Hostinger and business funding integration

The Hostinger adapter provides bounded, read-only website inventory with an
optional metadata receipt. It validates pagination and duplicate records before
reporting completion. The four-route funding registry preserves the latest
owner-supplied strings separately from unverified HTTPS candidates and earlier
source evidence. Its review packet keeps destination, attribution and publication
checks unresolved until verified.

The proposed site-inventory and funding-gateway mappings carry forward the prior
canonical domain and `/funding-readiness` design. They are ready to map to the
owner's actual workflow exports once identified. No Hostinger account connection,
site deployment, funding submission or shared remote memory is established by
these local modules. See [the proposed workflow mappings](docs/PROPOSED_HOSTINGER_WORKFLOW_MAPPINGS.md),
[Hostinger adapter](docs/HERMES_MEMPALACE_HOSTINGER.md) and
[funding review contract](docs/REFERRAL_CROSS_PLATFORM_INTEGRATION.md).

## Creative studio production

The Evolutionary Evolutions Creative Creations Studios of Intergalactic Corporate
Services LLC now has a fixed local configuration and a production-packet workflow.
It prepares reusable structures for Videos, eBooks, Audiobooks and Video Books,
six distribution briefs and three AI-workspace briefs. The exact owner-declared
brand and scope can also travel as optional business-context task data.

```bash
jarvis plan creative_studio_package "Prepare the studio intake packet" --json
jarvis run creative_studio_package "Prepare the studio intake packet" --json
```

The run creates a hashed template packet and a local review handoff before queuing
owner review. The packet remains `intake_required` and `template_only`; it contains
no rendered media and sends no handoffs. Existing approvals stop the workflow and
do not resume it automatically. Cached studio runs reverify the packet and its
retained manifest hash before reuse. Configuration changes produce a fresh run.
See [the studio workflow](docs/CREATIVE_STUDIO_WORKFLOW.md) for the packet contract,
offline verifier, intake fields and intended channel/workspace mappings.

For a filled assignment and actual local drafts, the structured production planner
creates a separate packet with source copies, exact source/parent hashes, the
Prompt #11 and studio-config snapshots, a derived plan, and three local workspace
handoff briefs. Changed sources and stale adaptations remain visible blockers.
The included [workforce publishing pilot](examples/studio-workforce-pilot/README.md)
contains an original Chapter 6 companion, narration, short-video script, video-book
storyboard, six channel-copy drafts, and a reader-experiment proposal.

```bash
jarvis studio-plan examples/studio-workforce-pilot/production-brief.json \
  --output /tmp/jarvis-workforce-pilot --json
jarvis verify-studio-plan /tmp/jarvis-workforce-pilot --json
jarvis studio-economics examples/studio-workforce-pilot/economics.json --json
```

Use a new output directory for each packet. `prepared_for_review` describes the
declared local text evidence; release remains blocked. The verifier reconstructs
the plan and handoffs, while retaining the limits of local hashes and untrusted
review assertions. The commands run before Control Tower initialization and make
no provider or account calls. See [the production contract](docs/STUDIO_PRODUCTION.md).

The economics command evaluates supplied assumptions in USD cents, including
whole-unit break-even counts and one-time labor opportunity cost. The pilot's
four scenarios are illustrative, with no actual sales or approved spending.
See [the calculation contract](docs/STUDIO_ECONOMICS.md). A dedicated Studio
production check builds this public example and retains verified packet/scenario
evidence in GitHub Actions; the separate public-metadata audit keeps its existing
scope. No rendered media, live workspace synchronization, Hostinger change, or
social release is established by these local checks.

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
