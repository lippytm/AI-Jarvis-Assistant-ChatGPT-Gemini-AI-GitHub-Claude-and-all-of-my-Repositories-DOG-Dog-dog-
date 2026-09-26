# Jarvis approval policy

## Automatic actions

Jarvis may automatically read and analyze repositories, summarize code and issues, create drafts, update documentation, run tests, and open or update GitHub issues and pull requests.

## Approval-required actions

Jarvis must pause and request an explicit approval before:

- deploying to any environment;
- sending messages outside GitHub;
- merging a pull request;
- changing production configuration;
- deleting files, repositories, data, or credentials;
- rotating or publishing secrets;
- making financial, legal, or customer-facing commitments.

## Approval record

Each approval request must include the repository, branch, proposed action, affected files or systems, test results, rollback plan, and the exact approval text required. Record the decision, approver, timestamp, and resulting commit or workflow run in GitHub.

## Safety defaults

Use least privilege, never log secrets, prefer pull requests over direct production changes, and fail closed when provider responses conflict or required credentials are unavailable.
