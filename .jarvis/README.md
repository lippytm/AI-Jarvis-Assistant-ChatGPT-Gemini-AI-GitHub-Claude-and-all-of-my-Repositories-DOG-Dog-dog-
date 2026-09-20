# AI Jarvis control plane

This directory defines the provider-neutral operating contract for AI Jarvis across GitHub, Gemini AI, ChatGPT Business, Claude, Hermes Fabric, and connected repositories.

## Source of truth

GitHub is authoritative for versioned instructions, agent policies, repository metadata, task state, approval records, and generated documentation. External model providers consume these files through adapters; they do not silently rewrite them.

## Operating cycle

1. A repository change triggers validation.
2. Jarvis reads the applicable instructions and repository context.
3. Jarvis may analyze, draft, and propose changes automatically.
4. Opening or updating issues and pull requests is allowed by policy.
5. Deployments, external messages, merges, and destructive changes require explicit approval.
6. Every approved action is recorded in GitHub.

## Required provider adapters

- `github`: repositories, files, issues, pull requests, Actions, and audit trail.
- `gemini`: analysis and document-oriented knowledge workflows.
- `openai`: ChatGPT Business-compatible planning and drafting workflows.
- `anthropic`: Claude-compatible review and reasoning workflows.
- `memory`: shared, versioned knowledge index; never store secrets.

Adapters must use environment variables or a secret manager. Never commit API keys, tokens, cookies, or private credentials.
