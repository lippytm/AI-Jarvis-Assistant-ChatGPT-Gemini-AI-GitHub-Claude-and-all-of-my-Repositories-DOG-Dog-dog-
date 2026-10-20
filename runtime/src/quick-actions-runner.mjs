import { authorizeQuickAction } from './quick-actions.mjs';

export function planQuickAction(input, env = process.env) {
  if (!input || !input.action) throw new Error('action is required');
  const decision = authorizeQuickAction(input.action, {
    repository: input.repository,
    pilotRepository: env.JARVIS_PILOT_REPOSITORY,
    // A request-body boolean is not an authenticated owner approval.
    approved: false
  });
  return {
    action: input.action,
    repository: input.repository || env.JARVIS_PILOT_REPOSITORY || null,
    decision,
    execute: false,
    note: decision.allowed ? 'Plan only; no worker has executed this action.' : 'Owner approval is required; this planner cannot grant it.'
  };
}
