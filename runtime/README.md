# AI Jarvis local runtime pilot

This Node.js 22+ service creates scoped task plans and, only with explicit local
configuration, requests advisory drafts from configured AI providers. It has no
execution worker: every response has `execute: false`. The service does not merge,
deploy, send messages, change secrets, run shell commands, or publish results.

## Start locally

From this directory:

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
execution. Without the runtime token and repository scope, `POST /tasks` returns
503 and cannot proceed.

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
`requestedAction`. Unknown fields, including `approved`, are rejected. Tasks are
limited to 8,000 characters; there may be at most 64 file labels of 512 characters
each. The entire UTF-8 JSON request is limited to 32 KiB. File labels are metadata;
the service never opens or executes them.

## Explicit advisory-provider mode

Provider calls require **both** `JARVIS_DRY_RUN=false` and
`JARVIS_ALLOW_EXTERNAL=true`, plus the runtime token, pilot scope, and the relevant
provider API credential. Setting only one switch does not enable a call.

Each accepted advisory task may call every configured OpenAI, Gemini, and
Anthropic provider once. Such calls can incur charges. Each request has a 30-second
deadline, a 2,000-output-token limit, no automatic retry, and a 1 MiB response-body
limit. The HTTP server allows only one provider task at a time and waits for all
started provider calls to finish before releasing that slot. Redirects are refused.
Provider failure returns a static error without the provider response body.

Provider model defaults are inherited from the existing adapters. Their current
availability and account permissions have not been verified by this local test
suite. Configure supported model identifiers in the private environment before a
separately authorized live test. Provider responses are independent drafts;
automated conflict resolution or approval is not implemented.

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
redacted failures, and provider request/response bounds.

HTTP headers are limited to 8 KiB, with a 10-second header timeout and a 15-second
request-body timeout. These transport settings are configured but are not a
production load or network-security test. There is no durable job queue,
cross-process concurrency control, aggregate spending budget, idempotency store,
TLS termination, shared identity service, or external MemPalace service here.
Repeated valid live-mode requests can incur repeated charges. Do not expose this
local pilot as a public production service. No runtime deployment is established
by adding these files or passing these tests.
