const QUICK_ACTION_ALIASES = Object.freeze({
  analyze: 'analyze_repository'
});

export const QUICK_ACTIONS = Object.freeze([
  { id: 'analyze_repository', label: 'Analyze repository', risk: 'low', mode: 'autonomous', capability: 'read_and_analyze' },
  { id: 'summarize_changes', label: 'Summarize changes', risk: 'low', mode: 'autonomous', capability: 'read_and_analyze' },
  { id: 'debug_failure', label: 'Debug a failure', risk: 'low', mode: 'autonomous', capability: 'read_and_analyze' },
  { id: 'self_heal_repository', label: 'Plan a self-healing repair', risk: 'medium', mode: 'autonomous', capability: 'create_draft' },
  { id: 'self_improve_workflow', label: 'Plan a self-improving update', risk: 'medium', mode: 'autonomous', capability: 'create_draft' },
  { id: 'run_tests', label: 'Run tests', risk: 'low', mode: 'autonomous', capability: 'test' },
  { id: 'sync_knowledge', label: 'Sync approved knowledge', risk: 'low', mode: 'autonomous', capability: 'write_versioned_knowledge' },
  { id: 'draft_issue', label: 'Draft an issue', risk: 'low', mode: 'autonomous', capability: 'create_draft' },
  { id: 'draft_pull_request', label: 'Draft a pull request', risk: 'low', mode: 'autonomous', capability: 'create_draft' },
  { id: 'notify_slack', label: 'Send Slack notification', risk: 'high', mode: 'approval_required', capability: 'send_external_message' },
  { id: 'deploy', label: 'Deploy', risk: 'high', mode: 'approval_required', capability: 'deploy' },
  { id: 'merge_pull_request', label: 'Merge pull request', risk: 'high', mode: 'approval_required', capability: 'merge' },
  { id: 'delete_resource', label: 'Delete resource', risk: 'critical', mode: 'approval_required', capability: 'destructive_change' },
  { id: 'change_secret', label: 'Change secret', risk: 'critical', mode: 'approval_required', capability: 'secret_change' }
]);

export function canonicalizeQuickActionId(id) {
  if (typeof id !== 'string') return id;
  const normalized = id.trim();
  return QUICK_ACTION_ALIASES[normalized] || normalized;
}

export function getQuickAction(id) {
  const action = QUICK_ACTIONS.find(item => item.id === canonicalizeQuickActionId(id));
  if (!action) throw new Error(`Unknown Quick Action: ${id}`);
  return action;
}

export function authorizeQuickAction(id, { repository, pilotRepository, approved = false } = {}) {
  const action = getQuickAction(id);
  if (repository && pilotRepository && repository !== pilotRepository) {
    throw new Error('Pilot mode refuses repositories outside JARVIS_PILOT_REPOSITORY');
  }
  if (action.mode === 'approval_required' && !approved) {
    return { allowed: false, status: 'approval_required', action };
  }
  return { allowed: true, status: 'ready', action };
}
