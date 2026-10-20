# Gemini Jarvis to ChatGPT Business migration

This procedure moves useful work without pretending that Gemini and ChatGPT share account
memory or private conversation history.

## 1. Export from Gemini

For each important Gemini Jarvis project, ask Gemini to produce one self-contained Markdown
handoff containing:

- Project name, purpose, audience, and current status
- Decisions already made and the reasoning behind them
- Architecture, prompts, workflows, and file inventory
- Open tasks, blockers, assumptions, and risks
- Source links and clear separation of verified facts from ideas
- Credentials required by name only—never include the credential values

Save the result as UTF-8 Markdown, for example `gemini-jarvis-product-factory.md`.

## 2. Capture it with Jarvis

```bash
jarvis intake gemini-ai-jarvis gemini-jarvis-product-factory.md \
  --title "Gemini Jarvis Product Factory" --json
```

Jarvis records the original filename, byte size, timestamp, and SHA-256 hash; scans for
common credential formats; stores a redacted copy; and creates a ChatGPT Business handoff.

## 3. Bring the handoff into ChatGPT Business

Open the generated `data/outbox/INTAKE_ID-chatgpt-business-intake.md`. Upload or paste that
file into the intended ChatGPT Business project. Ask ChatGPT to:

1. Preserve the intake ID in all derived plans.
2. Identify contradictions, missing files, and unsupported claims.
3. Produce a proposed merge plan before changing existing work.
4. Keep imported ideas separate from verified implementation status.

## 4. Run the multi-AI review

After resolving contradictions, feed the consolidated brief into
`multi_ai_business_review` or `prompt_11_product_factory`. Plan first, then explicitly enable
external providers only when credentials and spending limits are ready.

## 5. Return work to Gemini or GitHub

Create and verify a `.jarvis.zip` bundle. Transfer the bundle and record its SHA-256 at both
ends. This creates a traceable round trip instead of an untracked copy-and-paste cycle.

## Recommended migration order

1. AI Jarvis mission and governance
2. Prompt #11 and product-factory definitions
3. Active business/product projects
4. Repository architecture and integration plans
5. Content catalogs and creative-world notes
6. Backlog, experiments, and archived ideas
