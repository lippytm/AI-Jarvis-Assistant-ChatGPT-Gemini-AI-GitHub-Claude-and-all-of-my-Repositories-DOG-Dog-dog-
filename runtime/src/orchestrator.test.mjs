import assert from 'node:assert/strict';
import { buildPrompt, createEnvelope, selectAssistantProfile } from './orchestrator.mjs';

const debugEnvelope = createEnvelope({
  task: 'Debug the latest production error',
  category: 'incident',
  requestedAction: 'debug_failure',
  goals: ['restore service'],
  diagnostics: ['stack trace attached'],
  constraints: ['do not deploy automatically'],
  context: { branch: 'main' }
});

assert.equal(debugEnvelope.requestedAction, 'debug_failure');
assert.deepEqual(debugEnvelope.goals, ['restore service']);
assert.deepEqual(debugEnvelope.diagnostics, ['stack trace attached']);
assert.deepEqual(debugEnvelope.constraints, ['do not deploy automatically']);
assert.deepEqual(debugEnvelope.context, { branch: 'main' });
assert.equal(selectAssistantProfile(debugEnvelope).id, 'debug');
assert.match(buildPrompt(debugEnvelope), /validation_plan/);
assert.match(buildPrompt(debugEnvelope), /automation_opportunities/);

const selfHealEnvelope = createEnvelope({
  task: 'Create a self-healing fix for flaky repository checks',
  requestedAction: 'self_heal_repository'
});
assert.equal(selectAssistantProfile(selfHealEnvelope).id, 'self_heal');

const selfImproveEnvelope = createEnvelope({
  task: 'Improve the CI workflow for safer retries',
  requestedAction: 'self_improve_workflow'
});
assert.equal(selectAssistantProfile(selfImproveEnvelope).id, 'self_improve');

const matcherEnvelope = createEnvelope({
  task: 'Investigate the failing deployment incident',
  requestedAction: 'draft_issue'
});
assert.equal(selectAssistantProfile(matcherEnvelope).id, 'debug');

const diagnosticsEnvelope = createEnvelope({
  task: 'Prepare follow-up notes',
  requestedAction: 'draft_issue',
  diagnostics: ['root cause investigation pending'],
  constraints: ['keep changes in dry run'],
  context: { note: 'service recovery checklist' }
});
assert.equal(selectAssistantProfile(diagnosticsEnvelope).id, 'self_heal');

const standardEnvelope = createEnvelope({
  task: 'Summarize changes after a bug fix',
  requestedAction: 'summarize_changes'
});
assert.equal(selectAssistantProfile(standardEnvelope).id, 'standard');

const defaultEnvelope = createEnvelope({
  task: 'Analyze repository health'
});
assert.equal(defaultEnvelope.requestedAction, 'analyze_repository');

const legacyEnvelope = createEnvelope({
  task: 'Analyze repository health',
  requestedAction: 'analyze'
});
assert.equal(legacyEnvelope.requestedAction, 'analyze_repository');

console.log('Orchestrator assistant profile checks passed');
