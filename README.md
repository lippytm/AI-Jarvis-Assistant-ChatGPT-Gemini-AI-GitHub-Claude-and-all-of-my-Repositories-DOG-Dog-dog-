# AI Jarvis Assistant — Control Tower

An auditable, provider-neutral assistant that coordinates work across OpenAI, Gemini, Claude, GitHub, and future business systems without storing credentials in the repository.

> Status: **v0.1 foundation**. The CLI, task ledger, provider routing, mock mode, health checks, and tests are working. External providers require your own API keys and remain disabled until configured.

## What works now

- One task contract shared by every AI provider
- OpenAI, Anthropic Claude, Google Gemini, and offline mock adapters
- SQLite task, event, and response ledger with provenance
- Correlation IDs, timestamps, provider/model records, and response hashes
- Connector health checks that never reveal secrets
- Command-line interface with JSON output for automations
- GitHub Actions tests and dependency review
- Extension contract for GitHub, Hostinger, Slack, Zapier, and other connectors

## Architecture

```text
User / Automation -> Jarvis CLI -> Control Tower -> Provider Router
                                      |
                               Provenance ledger
```

Jarvis coordinates providers; it does not make them secretly communicate. Every cross-system handoff is an explicit, logged task. Human approval remains required for financial, publishing, credential, deletion, and production-deployment actions.

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .
jarvis health
jarvis ask "Create a three-step business launch checklist" --provider mock
jarvis history
```

The default is `mock`, so the project runs without paid API calls. Set environment variables described in [`.env.example`](.env.example) to enable a real provider. The CLI intentionally does not automatically load `.env`; a shell, secret manager, or deployment platform should inject secrets.

```bash
export JARVIS_DEFAULT_PROVIDER=openai
export OPENAI_API_KEY=replace-me
jarvis ask "Summarize this project" --provider openai
```

Never commit `.env`, tokens, passwords, OAuth refresh tokens, or customer data.

## Commands

```bash
jarvis health [--json]
jarvis ask "TASK" [--provider mock|openai|anthropic|gemini] [--system "..."] [--json]
jarvis history [--limit 20] [--json]
jarvis show TASK_ID [--json]
```

Future connectors implement `Connector` and declare read, draft, write, or destructive risk. Writes need explicit approval; destructive actions are disabled in v0.1. See [`docs/CONNECTORS.md`](docs/CONNECTORS.md) and [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m jarvis health --json
```

## Mission and naming

The mission is to build useful Jarvis connections across the places where Charles creates and operates businesses: ChatGPT, Gemini, Claude, GitHub, Hostinger, and related repositories. `Jarvis/DOG` is the canonical project identity; `Dog` and `dog` may be used as stylistic variants.

## License

CC0-1.0, matching the repository's existing license choice. Review it with qualified counsel before distributing a commercial product or accepting outside contributions.
