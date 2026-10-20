# AI Jarvis local runtime pilot

This Node.js 22+ service creates scoped task plans and, only with explicit local
configuration, requests advisory drafts from configured AI providers. It has no
execution worker: every response has `execute: false`. The service does not merge,
deploy, send messages, change secrets, run shell commands, or publish results.

## Start locally

Use a complete repository checkout containing both `runtime/` and
`config/prompt-11-profile.json`. From this directory:

```sh
npm run check
npm test
cp .env.example .env
```

Set `JARVIS_RUNTIME_TOKEN` in the private `.env` to a randomly generated, 32–256
character URL-safe token from your secret manager. Set
`JARVIS_PILOT_REPOSITORY` to the exact `owner/repository` being reviewed. Keep the
two provider switches at their defaults:

```text
JARVIS_HOST=127.0.0.1
JARVIS_PORT=8787
JARVIS_DRY_RUN=true
JARVIS_ALLOW_EXTERNAL=false
```

Then run `npm run start:local`, which explicitly loads `.env`. Plain `npm start`
uses variables already present in the process environment and does not load that
file. This pilot accepts only `127.0.0.1` or `::1` as its bind address.

`GET /health` needs no token and reports local configuration state. A health
response is not evidence of provider authentication, remote deployment, or worker
execution, and its `configured` field checks the runtime token and repository
scope only. Without those settings, `POST /tasks` returns 503 and cannot proceed.

## Shared Prompt #11 operating profile

The task planner loads the fixed repository profile `P-011-E6C-001`, revision
`repository-1`, from `config/prompt-11-profile.json`. The path resolves relative
to the runtime module, so it works when the working directory is `runtime/`.
Copying only the runtime directory omits a required dependency. An absent,
malformed, unrecognized or symlinked profile makes task requests fail with
HTTP 503 `prompt_profile_unavailable`, before any provider invocation. Health
responses do not validate this file.

Dry-run, approval-required plans and successful advisory results include:

```json
{
  "prompt_profile": {
    "id": "P-011-E6C-001",
    "revision": "repository-1",
    "sha256": "<SHA-256 of the exact profile file bytes>"
  },
  "profile_status": "resolved"
}
```

`resolved` records which local guidance was loaded. It does not claim a provider
was called, followed the guidance, or implemented an operational control. From
`runtime/`, `sha256sum ../config/prompt-11-profile.json` reproduces the hash; JSON
whitespace changes affect it. Python workflows use the same file and byte hash.

For advisory calls, the eight shared guidance sections and their authority
boundary precede the existing local advisory role in the providers' native
system-instruction fields. The task envelope remains user input. There is no
HTTP or environment option to supply another profile, file path, URL, revision
or system prompt. Changes require editing and reviewing the repository config.
This is a repository operating profile, with no claim of deployment to external
provider assistants, global swarm enforcement or recovered master-prompt text.

## Authenticated local plan

Every `POST /tasks` requires `Content-Type: application/json` and
`Authorization: Bearer <runtime token>`. The token is scoped to the single
configured pilot repository and grants planning/advisory access only. It never
serves as owner approval for a consequential action.

With the token also loaded into the **client's** environment from the secret
manager, a local example is:

```sh
curl --fail-with-body http://127.0.0.1:8787/tasks \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${JARVIS_RUNTIME_TOKEN}" \
  --data '{"task":"Prepare a review plan for the supplied change.","requestedAction":"analyze"}'
```

Loading `.env` in the server does not export its token into another terminal.
The request above defaults to the configured repository. A different repository
is rejected with 403. Dry-run returns `status: dry_run`, no provider results, and
`execute: false`, even if provider API keys are present.

Accepted fields are `task` (required), `id`, `category`, `repository`, `files`, and
`requestedAction`. Unknown fields, including `approved` and `prompt_profile`, are rejected. Tasks are
limited to 8,000 characters; there may be at most 64 file labels of 512 characters
each. The entire UTF-8 JSON request is limited to 32 KiB. File labels are metadata;
the service never opens or executes them.

## Explicit advisory-provider mode

Provider calls require **both** `JARVIS_DRY_RUN=false` and
`JARVIS_ALLOW_EXTERNAL=true`, plus the runtime token, pilot scope, valid fixed
profile, and the relevant provider API credential and explicit model ID. Setting
only one switch does not enable a call.

Set `OPENAI_MODEL`, `GEMINI_MODEL` or `ANTHROPIC_MODEL` for every corresponding API
key present in the server environment. There are no silent model defaults. IDs
must be 1–256 characters without whitespace or control characters. A keyed
provider without a valid model setting blocks the entire advisory task with
HTTP 503 `provider_models_not_configured`; it is not silently omitted.
Dry-run and approval-required plans do not need provider credentials or models.

Each accepted advisory task may call every configured OpenAI, Gemini, and
Anthropic provider once. Such calls can incur charges. Each request has a 30-second
deadline, a 2,000-token generation cap, no automatic retry, and a 1 MiB response-body
limit. The HTTP server allows only one provider task at a time and waits for all
started provider calls to finish before releasing that slot. Redirects are refused.
Provider failure returns a static error without the provider response body.

An HTTP 2xx response is accepted only when its body is a nonempty, strictly
decoded UTF-8 JSON object containing completed, nonblank draft text in the
provider's native fields. Every returned OpenAI choice must end with `stop`;
every Gemini candidate must end with `STOP`; Anthropic must end with `end_turn`
or `stop_sequence`. Empty drafts, malformed bodies, refusals, blocked responses,
truncated generations and unsupported completion states fail with HTTP 502
`provider_request_failed`. Thinking-only content is not a draft. A failure from
any selected provider prevents `draft_ready`, even if other providers succeed.
Valid provider responses retain their original JSON shape and metadata. These
checks establish the presence of completed text, not its factual accuracy or
fulfilment of the task's requested output schema.

Choose model IDs compatible with the respective adapter and your account before
a separately authorized live test. OpenAI uses Chat Completions with native
`system` messages and `max_completion_tokens` (which includes reasoning tokens),
and does not force a temperature setting. Gemini uses `generateContent` with
`systemInstruction`; Anthropic uses Messages with a top-level `system` field.
Local checks do not verify live model availability, account permissions or every
model's parameter support. Provider responses are independent drafts; automated
conflict resolution or approval is not implemented.

## Quick Actions and release boundaries

The existing Quick Actions remain non-executing plans. Deployment, merging,
deletion, external messaging, secret changes, and financial commitments return an
approval-required plan before any provider call. A request-body `approved: true`
cannot release that stop, including through the separate Quick Action planner.
There is no HTTP approval endpoint or consequential worker in this pilot.

## Verification and limits

`npm test` runs the Quick Action policy checks and `node:test` regression suites.
The new tests use in-memory request streams and stubbed provider functions/fetch;
they open no network socket and contact no provider. They check dry-run isolation,
authentication, repository scope, external opt-in, body validation, concurrency,
redacted failures, explicit model configuration, and provider request/response
bounds. Profile regressions use temporary repository layouts to check missing or
invalid config without modifying the real shared profile, and verify guidance in
all three native system fields and matching result provenance. Provider tests
use completed native response fixtures and verify that invalid, blocked or
truncated responses cannot become successful advisory results.

HTTP headers are limited to 8 KiB, with a 10-second header timeout and a 15-second
request-body timeout. These transport settings are configured but are not a
production load or network-security test. There is no durable job queue,
cross-process concurrency control, aggregate spending budget, idempotency store,
TLS termination, shared identity service, or external MemPalace service here.
Repeated valid live-mode requests can incur repeated charges. Do not expose this
local pilot as a public production service. No runtime deployment is established
by adding these files or passing these tests.
