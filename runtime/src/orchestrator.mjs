import { canonicalizeQuickActionId, getQuickAction } from './quick-actions.mjs';
import { askClaude, askGemini, askOpenAI, configuredProviders } from './providers.mjs';

const approvalRequired = new Set(['deploy', 'merge', 'delete', 'external_message', 'secret_change', 'financial_commitment']);
const assistantProfiles = [
  {
    id: 'self_heal',
    actions: new Set(['self_heal_repository']),
    matcher: /(self[- ]?heal|repair plan|service recovery|recover from|hotfix)/i,
    instructions: 'Focus on root cause, smallest safe repair, rollback steps, and post-fix validation.'
  },
  {
    id: 'self_improve',
    actions: new Set(['self_improve_workflow']),
    matcher: /(self[- ]?improv|continuous improvement|optimi[sz]e|streamline|refactor)/i,
    instructions: 'Focus on durable improvements, measurable gains, safety checks, and follow-up automation.'
  },
  {
    id: 'debug',
    actions: new Set(['debug_failure']),
    matcher: /(debug|troubleshoot|investigat(?:e|ion)|root cause|failing|failure|incident|regression)/i,
    instructions: 'Focus on reproducing the issue, isolating likely causes, risk-ranked fixes, and evidence to collect.'
  }
];

function resolveRequestedAction(value) {
  const trimmedValue = typeof value === 'string' ? value.trim() : value;
  const normalizedValue = canonicalizeQuickActionId(trimmedValue);
  if (trimmedValue === undefined || trimmedValue === null) {
    return { canonicalRequestedAction: 'analyze_repository', requestedActionSource: 'default' };
  }
  if (trimmedValue === '') {
    return { canonicalRequestedAction: 'analyze_repository', requestedActionSource: 'default' };
  }
  if (trimmedValue === 'analyze') return { canonicalRequestedAction: 'analyze_repository', requestedActionSource: 'legacy' };
  return { canonicalRequestedAction: normalizedValue, requestedActionSource: 'explicit' };
}

function serializeSearchValue(value) {
  if (value === undefined || value === null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'bigint') return value.toString();
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return '[object]';
    }
  }
  return String(value);
}

function flattenSearchValues(value) {
  const visit = (nestedValue, ancestors = new Set()) => {
    if (nestedValue === undefined || nestedValue === null) return [];
    if (Array.isArray(nestedValue)) return nestedValue.flatMap(item => visit(item, ancestors));
    if (typeof nestedValue === 'object') {
      if (ancestors.has(nestedValue)) return ['[circular]'];
      const nextAncestors = new Set(ancestors);
      nextAncestors.add(nestedValue);
      return Object.entries(nestedValue).flatMap(([key, childValue]) => [key, ...visit(childValue, nextAncestors)]);
    }
    return [serializeSearchValue(nestedValue)];
  };
  return visit(value);
}

function safeStringify(value) {
  const sanitize = (nestedValue, path = []) => {
    if (typeof nestedValue === 'bigint') return nestedValue.toString();
    if (!nestedValue || typeof nestedValue !== 'object') return nestedValue;
    if (path.includes(nestedValue)) return '[circular]';
    const nextPath = [...path, nestedValue];
    if (Array.isArray(nestedValue)) {
      return nestedValue.map(item => sanitize(item, nextPath));
    }
    return Object.fromEntries(
      Object.entries(nestedValue).map(([key, childValue]) => [key, sanitize(childValue, nextPath)])
    );
  };
  return JSON.stringify(sanitize(value), null, 2);
}

export function createEnvelope(input) {
  if (!input || typeof input !== 'object' || !input.task) throw new Error('A task is required');
  const originalRequestedAction = Object.hasOwn(input, 'requestedAction') ? input.requestedAction : null;
  const { canonicalRequestedAction, requestedActionSource } = resolveRequestedAction(input.requestedAction);
  return {
    id: input.id || crypto.randomUUID(),
    task: String(input.task),
    category: input.category || 'unknown',
    repository: input.repository || null,
    files: Array.isArray(input.files) ? input.files : [],
    diagnostics: Array.isArray(input.diagnostics) ? input.diagnostics : [],
    goals: Array.isArray(input.goals) ? input.goals : [],
    constraints: Array.isArray(input.constraints) ? input.constraints : [],
    context: input.context && typeof input.context === 'object' ? input.context : {},
    originalRequestedAction,
    requestedAction: originalRequestedAction ?? 'analyze',
    canonicalRequestedAction,
    requestedActionSource,
    createdAt: new Date().toISOString()
  };
}

export function selectAssistantProfile(envelope) {
  const action = envelope.canonicalRequestedAction || envelope.requestedAction;
  for (const profile of assistantProfiles) {
    if (profile.actions.has(action)) {
      return profile;
    }
  }
  const searchable = [
    envelope.task,
    envelope.category,
    envelope.requestedAction,
    envelope.canonicalRequestedAction,
    ...envelope.goals,
    ...envelope.diagnostics,
    ...envelope.constraints,
    ...flattenSearchValues(envelope.context)
  ].map(serializeSearchValue).join(' ');
  for (const profile of assistantProfiles) {
    if (profile.matcher.test(searchable)) {
      return profile;
    }
  }
  return {
    id: 'standard',
    instructions: 'Focus on repository-safe analysis, explicit risks, and actionable next steps.'
  };
}

export function buildPrompt(envelope, profile = selectAssistantProfile(envelope)) {
  return `You are one member of a governed multi-agent system. Return JSON with findings, risks, proposed_actions, questions, validation_plan, and automation_opportunities. Do not execute anything.

Assistant profile: ${profile.id}
Profile instructions: ${profile.instructions}

Task envelope:
${safeStringify(envelope)}`;
}

export async function orchestrate(input, env = process.env) {
  const envelope = createEnvelope(input);
  getQuickAction(envelope.canonicalRequestedAction || envelope.requestedAction);
  const available = configuredProviders(env);
  const assistantProfile = selectAssistantProfile(envelope);
  const prompt = buildPrompt(envelope, assistantProfile);
  const results = {};
  const calls = [];
  if (available.openai) calls.push(askOpenAI(prompt, env).then(value => { results.openai = value; }));
  if (available.gemini) calls.push(askGemini(prompt, env).then(value => { results.gemini = value; }));
  if (available.anthropic) calls.push(askClaude(prompt, env).then(value => { results.anthropic = value; }));
  if (!calls.length) throw new Error('No AI provider credentials are configured; refusing to guess or execute');
  await Promise.all(calls);
  return {
    envelope,
    assistantProfile: assistantProfile.id,
    providersUsed: Object.keys(results),
    results,
    status: approvalRequired.has(envelope.canonicalRequestedAction || envelope.requestedAction) ? 'approval_required' : 'draft_ready',
    execute: false
  };
}
