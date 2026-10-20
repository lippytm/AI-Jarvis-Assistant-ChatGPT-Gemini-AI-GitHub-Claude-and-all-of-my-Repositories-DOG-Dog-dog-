import { randomUUID } from 'node:crypto';
import { askClaude, askGemini, askOpenAI, configuredProviders } from './providers.mjs';
import { QUICK_ACTIONS } from './quick-actions.mjs';

const approvalRequired = new Set([
  'deploy', 'merge', 'delete', 'external_message', 'secret_change', 'financial_commitment',
  ...QUICK_ACTIONS.filter(action => action.mode === 'approval_required').map(action => action.id)
]);
const supportedActions = new Set([
  'analyze', 'summarize', 'review', 'draft', ...approvalRequired,
  ...QUICK_ACTIONS.map(action => action.id)
]);
const inputFields = new Set(['id', 'task', 'category', 'repository', 'files', 'requestedAction']);
const repositoryPattern = /^[A-Za-z0-9][A-Za-z0-9_.-]*\/[A-Za-z0-9][A-Za-z0-9_.-]*$/;

export class RuntimeError extends Error {
  constructor(status, code) {
    super(code);
    this.status = status;
    this.code = code;
  }
}

export function validRepository(value) {
  return typeof value === 'string' && value.length <= 256 && repositoryPattern.test(value);
}

function boundedString(value, max, code) {
  if (typeof value !== 'string' || !value.trim() || value.length > max || value.includes('\0')) {
    throw new RuntimeError(400, code);
  }
  return value;
}

export function createEnvelope(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new RuntimeError(400, 'invalid_task_object');
  }
  if (Object.keys(input).some(key => !inputFields.has(key))) {
    throw new RuntimeError(400, 'unknown_task_field');
  }
  const task = boundedString(input.task, 8000, 'invalid_task');
  const id = input.id === undefined ? randomUUID() : boundedString(input.id, 128, 'invalid_id');
  const category = input.category === undefined ? 'unknown' : boundedString(input.category, 64, 'invalid_category');
  if (input.repository !== undefined && !validRepository(input.repository)) {
    throw new RuntimeError(400, 'invalid_repository');
  }
  const files = input.files === undefined ? [] : input.files;
  if (!Array.isArray(files) || files.length > 64) throw new RuntimeError(400, 'invalid_files');
  for (const file of files) boundedString(file, 512, 'invalid_file');
  const requestedAction = input.requestedAction === undefined ? 'analyze' : input.requestedAction;
  if (!supportedActions.has(requestedAction)) throw new RuntimeError(400, 'unknown_requested_action');
  return {
    id, task, category, repository: input.repository ?? null,
    files: [...files], requestedAction, createdAt: new Date().toISOString()
  };
}

export function planTask(input, env = process.env) {
  const envelope = createEnvelope(input);
  if (!validRepository(env.JARVIS_PILOT_REPOSITORY)) {
    throw new RuntimeError(503, 'pilot_repository_not_configured');
  }
  if (envelope.repository && envelope.repository !== env.JARVIS_PILOT_REPOSITORY) {
    throw new RuntimeError(403, 'repository_outside_pilot_scope');
  }
  envelope.repository = env.JARVIS_PILOT_REPOSITORY;
  return {
    envelope,
    providersUsed: [],
    results: {},
    status: approvalRequired.has(envelope.requestedAction) ? 'approval_required' : 'dry_run',
    execute: false
  };
}

export async function orchestrate(input, env = process.env, providerCalls = {
  openai: askOpenAI, gemini: askGemini, anthropic: askClaude
}) {
  const plan = planTask(input, env);
  // Keep the no-network and approval stops inside this API as well as the HTTP route.
  if (plan.status === 'approval_required' || env.JARVIS_DRY_RUN !== 'false') return plan;
  if (env.JARVIS_ALLOW_EXTERNAL !== 'true') throw new RuntimeError(403, 'external_invocation_disabled');
  const available = configuredProviders(env);
  const providers = ['openai', 'gemini', 'anthropic'].filter(name => available[name]);
  if (!providers.length) throw new RuntimeError(503, 'provider_credentials_not_configured');
  const prompt = `You are one member of a governed multi-agent system. Return JSON with findings, risks, proposed_actions, and questions. Do not execute anything.\n\nTask envelope:\n${JSON.stringify(plan.envelope, null, 2)}`;
  const results = {};
  const outcomes = await Promise.allSettled(providers.map(async name => {
    results[name] = await providerCalls[name](prompt, env);
  }));
  if (outcomes.some(outcome => outcome.status === 'rejected')) {
    // Provider bodies and request URLs may contain private data or credentials.
    throw new RuntimeError(502, 'provider_request_failed');
  }
  return { ...plan, providersUsed: providers, results, status: 'draft_ready', execute: false };
}
