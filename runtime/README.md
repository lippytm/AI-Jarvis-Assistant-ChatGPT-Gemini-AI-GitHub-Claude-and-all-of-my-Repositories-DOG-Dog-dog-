# AI Jarvis runtime

This is the provider-neutral coordination layer. It runs in fail-closed pilot mode: missing credentials, repositories outside the configured pilot repository, conflicting results, and high-impact actions stop before execution.

When a task includes a repository in `owner/name` format, the runtime checks access to its GitHub repository API using `GITHUB_TOKEN`. The token must already be authorized for that repository; this check does not grant access, enumerate repositories, or fetch source files.

`OPENAI_API_KEY` is for the OpenAI API. It is not a ChatGPT or ChatGPT Business sign-in, subscription credential, or GitHub connector authorization. Configure the ChatGPT GitHub connector separately in ChatGPT and authorize the desired repositories there. For Jarvis, grant the GitHub App or token access in GitHub, and expand beyond the single-repository pilot only after the documented approval gate.

## Quick Actions

The registry includes repository analysis, change summaries, tests, versioned knowledge sync, issue and pull-request drafts, Slack notifications, deployment, merging, deletion, and secret changes. Low-risk actions may run autonomously. External, destructive, deployment, merge, and secret actions require explicit approval.

## Validation

Run `npm run check` and `npm test`. Copy `.env.example` into the deployment environment and provide credentials through the secret manager, not Git.

The current runner creates and validates execution plans. It does not directly merge, deploy, delete, send external messages, or alter secrets. Those actions must be separately authenticated workers after Hermes Fabric and GitHub approval integration are available.
