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
  if (!value) return { requestedAction: 'analyze_repository', requestedActionSource: 'default' };
  if (value === 'analyze') return { requestedAction: 'analyze_repository', requestedActionSource: 'legacy' };
  return { requestedAction: value, requestedActionSource: 'explicit' };
}

export function createEnvelope(input) {
  if (!input || typeof input !== 'object' || !input.task) throw new Error('A task is required');
  const { requestedAction, requestedActionSource } = resolveRequestedAction(input.requestedAction);
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
    originalRequestedAction: input.requestedAction || null,
    requestedAction,
    requestedActionSource,
    createdAt: new Date().toISOString()
  };
}

export function selectAssistantProfile(envelope) {
  for (const profile of assistantProfiles) {
    if (profile.actions.has(envelope.requestedAction)) {
      return profile;
    }
  }
  const searchable = [
    envelope.task,
    envelope.category,
    envelope.requestedAction,
    ...envelope.goals,
    ...envelope.diagnostics,
    ...envelope.constraints,
    ...Object.values(envelope.context).map(value => String(value))
  ].join(' ');
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
${JSON.stringify(envelope, null, 2)}`;
}

export async function orchestrate(input, env = process.env) {
  const envelope = createEnvelope(input);
  const available = configuredProviders(env);
  const assistantProfile = selectAssistantProfile(envelope);
  const prompt = buildPrompt(envelope, assistantProfile);
  const approvalActions = [envelope.requestedAction, envelope.originalRequestedAction].filter(Boolean);
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
    status: approvalActions.some(action => approvalRequired.has(action)) ? 'approval_required' : 'draft_ready',
    execute: false
  };
}
