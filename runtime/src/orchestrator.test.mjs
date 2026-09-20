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
  requestedAction: 'run_tests'
});
assert.equal(selectAssistantProfile(matcherEnvelope).id, 'debug');

const diagnosticsEnvelope = createEnvelope({
  task: 'Prepare follow-up notes',
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
assert.equal(defaultEnvelope.requestedActionSource, 'default');
assert.equal(defaultEnvelope.originalRequestedAction, null);

const legacyEnvelope = createEnvelope({
  task: 'Analyze repository health',
  requestedAction: 'analyze'
});
assert.equal(legacyEnvelope.requestedAction, 'analyze_repository');
assert.equal(legacyEnvelope.requestedActionSource, 'legacy');
assert.equal(legacyEnvelope.originalRequestedAction, 'analyze');

const emptyActionEnvelope = createEnvelope({
  task: 'Analyze repository health',
  requestedAction: ''
});
assert.equal(emptyActionEnvelope.originalRequestedAction, '');
assert.equal(emptyActionEnvelope.requestedAction, 'analyze_repository');
assert.equal(emptyActionEnvelope.requestedActionSource, 'explicit');

const falseActionEnvelope = createEnvelope({
  task: 'Analyze repository health',
  requestedAction: false
});
assert.equal(falseActionEnvelope.requestedAction, false);
assert.equal(falseActionEnvelope.requestedActionSource, 'explicit');

const paddedLegacyEnvelope = createEnvelope({
  task: 'Analyze repository health',
  requestedAction: ' analyze '
});
assert.equal(paddedLegacyEnvelope.requestedAction, 'analyze_repository');
assert.equal(paddedLegacyEnvelope.requestedActionSource, 'legacy');

console.log('Orchestrator assistant profile checks passed');
