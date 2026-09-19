# Capability matrix

| System | Automated capability | Requires credential | External write |
|---|---|---:|---:|
| Mock Jarvis | Offline task and workflow verification | No | No |
| OpenAI API | Responses-based generation | Yes | No |
| ChatGPT profile | OpenAI API generation for ChatGPT-directed work | Yes | No |
| ChatGPT Business | Verified draft handoff bundle | No | No |
| Gemini | Content generation | Yes | No |
| Gemini Jarvis | Gemini-backed Jarvis specialist workflow | Yes | No |
| Claude | Architecture and QA review | Yes | No |
| Perplexity | Research response with available citations | Yes | No |
| GitHub | Public or token-scoped repository inventory | Optional | No |
| Hostinger | Documented future connector boundary | Yes | Not implemented |
| Gemini/Claude exports | Provenance-recorded intake and Business handoff | No | No |

“Configured” means the required environment variable exists. It does not prove that a key is
valid, funded, correctly scoped, or accepted until an explicitly authorized live request runs.

ChatGPT and ChatGPT Business subscriptions do not automatically provide OpenAI API credits.
The API and workspace are intentionally modeled as separate surfaces.
