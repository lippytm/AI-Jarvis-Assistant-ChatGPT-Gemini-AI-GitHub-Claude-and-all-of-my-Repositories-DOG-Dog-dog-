import assert from 'node:assert/strict';
import { authorizeQuickAction, QUICK_ACTIONS } from './quick-actions.mjs';

assert.equal(QUICK_ACTIONS.length, 11);
assert.equal(authorizeQuickAction('run_tests', { repository: 'pilot', pilotRepository: 'pilot' }).allowed, true);
assert.equal(authorizeQuickAction('deploy', { repository: 'pilot', pilotRepository: 'pilot' }).status, 'approval_required');
assert.throws(() => authorizeQuickAction('run_tests', { repository: 'other', pilotRepository: 'pilot' }), /Pilot mode/);
console.log('Quick Actions policy checks passed');
