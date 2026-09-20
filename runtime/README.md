# AI Jarvis runtime

This is the provider-neutral coordination layer. It runs in fail-closed pilot mode: missing credentials, repositories outside the configured pilot repository, conflicting results, and high-impact actions stop before execution.

## Quick Actions

The registry includes repository analysis, debugging, self-healing repair planning, self-improvement planning, change summaries, tests, versioned knowledge sync, issue and pull-request drafts, Slack notifications, deployment, merging, deletion, and secret changes. Low-risk actions may run autonomously. External, destructive, deployment, merge, and secret actions require explicit approval.

## Validation

Run `npm run check` and `npm test`. Copy `.env.example` into the deployment environment and provide credentials through the secret manager, not Git.

The current runner creates and validates execution plans. Self-healing, self-improving, and debugging requests are routed through dedicated assistant profiles so provider responses include repair plans, validation steps, and automation opportunities without directly executing changes. The runtime does not directly merge, deploy, delete, send external messages, or alter secrets. Those actions must be separately authenticated workers after Hermes Fabric and GitHub approval integration are available.
