import { askClaude, askGemini, askOpenAI, configuredProviders } from './providers.mjs';

const approvalRequired = new Set(['deploy', 'merge', 'delete', 'external_message', 'secret_change', 'financial_commitment']);

export function createEnvelope(input) {
  if (!input || typeof input !== 'object' || !input.task) throw new Error('A task is required');
  return {
    id: input.id || crypto.randomUUID(),
    task: String(input.task),
    category: input.category || 'unknown',
    repository: input.repository || null,
    files: Array.isArray(input.files) ? input.files : [],
    requestedAction: input.requestedAction || 'analyze',
    createdAt: new Date().toISOString()
  };
}

export async function orchestrate(input, env = process.env) {
  const envelope = createEnvelope(input);
  const available = configuredProviders(env);
  const prompt = `You are one member of a governed multi-agent system. Return JSON with findings, risks, proposed_actions, and questions. Do not execute anything.\n\nTask envelope:\n${JSON.stringify(envelope, null, 2)}`;
  const results = {};
  const calls = [];
  if (available.openai) calls.push(askOpenAI(prompt, env).then(value => { results.openai = value; }));
  if (available.gemini) calls.push(askGemini(prompt, env).then(value => { results.gemini = value; }));
  if (available.anthropic) calls.push(askClaude(prompt, env).then(value => { results.anthropic = value; }));
  if (!calls.length) throw new Error('No AI provider credentials are configured; refusing to guess or execute');
  await Promise.all(calls);
  return {
    envelope,
    providersUsed: Object.keys(results),
    results,
    status: approvalRequired.has(envelope.requestedAction) ? 'approval_required' : 'draft_ready',
    execute: false
  };
}
