# Security policy

Do not open a public issue containing a credential, private customer record, or exploitable security detail. Revoke exposed credentials immediately and contact the owner privately.

- Use separate, least-privilege credentials for each connector.
- Store secrets in the deployment platform or GitHub Actions secrets.
- Never commit `.env` or copy secrets into AI prompts.
- Require human approval for publishing, sending, spending, deleting, or production deployment.
- Treat provider output as untrusted input before executing commands or rendering HTML.
- Do not place regulated or highly sensitive data in the local SQLite ledger.

The v0.1 foundation is not suitable for autonomous financial transactions, production secrets, or unattended destructive actions.

Enable GitHub's Dependency Graph in repository security settings before adding the
`actions/dependency-review-action` workflow; GitHub rejects that action when the graph is disabled.
