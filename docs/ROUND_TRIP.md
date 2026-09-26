# Provenance-preserving round trips

Jarvis transfer bundles move completed work between ChatGPT Business, Gemini, Claude,
GitHub, Hostinger, and other workstations without implying shared hidden memory.

## Bundle contents

- Redacted workflow run report
- Draft handoff documents produced by the run
- `manifest.json` using schema `jarvis.bundle.v1`
- Byte size and SHA-256 digest for every artifact
- Bundle-level SHA-256 digest returned by the CLI

## Create and verify

```bash
jarvis bundle RUN_ID --json
jarvis verify-bundle data/bundles/RUN_ID.jarvis.zip --json
```

Verify a bundle before uploading it to another system. The verifier rejects missing or
additional artifacts, changed bytes, duplicate archive paths, path traversal, unsupported
schemas, and oversized payloads.

## Receiving-station procedure

1. Record the bundle SHA-256 shown by the sending station.
2. Transfer the `.jarvis.zip` without modifying it.
3. Run `verify-bundle` at the receiving station.
4. Compare the bundle SHA-256 values.
5. Read the manifest and run report before using any handoff.
6. Create a new run for follow-up work and retain the source run ID in its input or metadata.

Bundles are transport artifacts, not credential containers. Never add `.env`, tokens,
passwords, private customer data, or secret-manager exports to a bundle.
