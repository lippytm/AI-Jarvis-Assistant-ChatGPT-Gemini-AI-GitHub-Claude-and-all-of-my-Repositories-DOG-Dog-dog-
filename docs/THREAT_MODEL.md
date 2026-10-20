# Threat model

## Protected assets

- Provider and connector credentials
- Customer and business information
- Workflow provenance and approval history
- Repository source and deployment access
- Provider spending limits

## Principal threats and controls

| Threat | Current control | Remaining work |
|---|---|---|
| Credential committed to Git | `.env` ignored; scanner blocks common key formats | Add platform secret scanning |
| Prompt injection requests actions | Outputs are untrusted; writes require separate approval | Add connector-specific policy tests |
| Repeated paid calls | Idempotency and external-call budget | Add provider-specific dollar budgets |
| Tampered handoff | Manifest and SHA-256 verification | Add optional digital signatures |
| Unsafe archive | Traversal, duplicate, size, and manifest checks | Fuzz testing |
| Excessive GitHub access | Public reads by default; optional scoped token | GitHub App with per-repo installation |
| Unattended destructive action | Destructive connector actions disabled | Multi-party authorization if ever enabled |
| Sensitive data retained locally | Credential redaction and documented restrictions | Encryption and retention automation |

## Trust boundaries

AI provider output, repository content, webpages, bundle contents, webhook payloads, and user
supplied workflow definitions are untrusted. They may inform a draft but cannot grant their own
approval, expand permissions, reveal secrets, or authorize execution.
