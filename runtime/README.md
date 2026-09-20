# AI Jarvis runtime

This is the provider-neutral coordination layer. It runs in fail-closed mode: missing credentials, conflicting results, and high-impact actions stop before execution.

## Local validation

Run `npm run check`, then start with `npm start`. Copy `.env.example` into the deployment environment and provide credentials through the secret manager, not Git.

## Task intake

POST a JSON task to `/tasks` with `task`, and optionally `category`, `repository`, `files`, and `requestedAction`. The runtime asks each configured provider independently, returns a draft, and marks high-impact actions as `approval_required`.

This runtime does not merge, deploy, delete, send external messages, or alter secrets. Those actions must be implemented as separately authenticated workers after Hermes Fabric and GitHub approval integration are available.
