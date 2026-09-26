import { authorizeQuickAction } from './quick-actions.mjs';

export function planQuickAction(input, env = process.env) {
  if (!input || !input.action) throw new Error('action is required');
  const decision = authorizeQuickAction(input.action, {
    repository: input.repository,
    pilotRepository: env.JARVIS_PILOT_REPOSITORY,
    approved: input.approved === true
  });
  return {
    action: input.action,
    repository: input.repository || env.JARVIS_PILOT_REPOSITORY || null,
    decision,
    execute: false,
    note: decision.allowed ? 'Action is approved for the pilot runner.' : 'Action is paused until explicit approval.'
  };
}
