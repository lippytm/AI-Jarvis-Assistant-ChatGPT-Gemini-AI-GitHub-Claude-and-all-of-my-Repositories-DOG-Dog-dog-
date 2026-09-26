# AI Jarvis operating contract

Jarvis coordinates Gemini AI, ChatGPT Business, Claude, GitHub, Hermes Fabric, and shared memory through a common contract.

## Shared context

Every provider receives the same task envelope:

- objective and acceptance criteria;
- relevant repository, branch, issue, or pull request;
- current instructions and knowledge references;
- files changed or proposed;
- test results and unresolved risks;
- approval status.

## Provider independence

A provider may recommend, analyze, or draft, but GitHub remains the canonical record. Provider-specific prompts must be stored as versioned files and reviewed like code. No provider may treat its private conversation history as canonical shared memory.

## Task lifecycle

`intake -> analyze -> draft -> validate -> approval_if_required -> execute -> record`

Tasks that fail validation or produce conflicting instructions move to `blocked` and open a review issue instead of executing.

## Synchronization rule

Synchronize on repository changes. A synchronization run must be idempotent: re-running it with no relevant changes produces no duplicate issue, document, message, or deployment.
