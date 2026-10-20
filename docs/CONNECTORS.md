# Connector contract

Jarvis integrations must be explicit, least-privilege, and auditable.

1. Validate configuration without printing secret values.
2. Convert the request into a typed `ConnectorAction`.
3. Classify risk as read, draft, write, or destructive.
4. Require approval for writes; refuse destructive actions in v0.1.
5. Execute with the narrowest available permission.
6. Record the result, external identifier, timestamps, and a content hash.

| System | First safe capability | Authentication |
|---|---|---|
| GitHub | Read repository state; draft issues/PRs | GitHub App or fine-grained token |
| Hostinger | Read deployment status; prepare deployment | Scoped API token |
| Slack | Draft updates; send only after approval | OAuth bot token |
| Zapier | Emit signed task events | Webhook secret |
| HubSpot | Read CRM context; draft updates | Private app/OAuth |
| Airtable | Read/write Idea Ledger records | OAuth/personal access token |

Never pass one provider's API key to another provider. Tokens belong in a secret manager, not prompts, logs, or Git.
