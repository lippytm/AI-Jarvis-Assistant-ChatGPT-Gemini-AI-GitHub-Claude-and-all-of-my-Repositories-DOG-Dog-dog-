# Jarvis deployment readiness

## Completed in repository

- Provider role contracts
- Repository-wide scope policy
- Versioned knowledge schema
- Approval policy
- Fail-closed runtime
- Independent provider calls for OpenAI, Gemini, and Claude
- Runtime health endpoint and task intake
- CI syntax validation

## Required outside the repository

1. Create provider credentials in a secret manager.
2. Configure Hermes Fabric's endpoint and token.
3. Configure a GitHub App or token with the minimum required permissions.
4. Configure Slack and Notion tokens if notifications or the knowledge mirror are wanted.
5. Deploy the runtime in a private environment.
6. Run sandbox tests with `JARVIS_DRY_RUN=true`.
7. Review provider output conflicts and approve a staged pilot repository.
8. Expand repository coverage only after the pilot passes.

No credential values belong in this repository. Production execution must remain disabled until the approval and rollback tests pass.
