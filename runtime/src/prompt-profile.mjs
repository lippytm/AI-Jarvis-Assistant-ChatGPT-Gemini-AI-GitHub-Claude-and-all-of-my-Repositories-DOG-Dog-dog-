import { createHash } from 'node:crypto';
import { lstatSync, readFileSync } from 'node:fs';

const PROFILE_ID = 'P-011-E6C-001';
const PROFILE_REVISION = 'repository-1';
// Resolve from this module, including when npm runs from runtime/. No caller or
// environment value can select another profile file or a remote instruction URL.
const PROFILE_PATH = new URL('../../config/prompt-11-profile.json', import.meta.url);
const GUIDANCE_SECTIONS = [
  'objective_and_done', 'tools_data_and_budgets', 'approvals',
  'provenance_and_evidence', 'independent_qa', 'handoff_idempotency',
  'stop_and_rollback', 'scoped_memory'
];

export class PromptProfileError extends Error {}

function uniqueJson(source) {
  const value = JSON.parse(source);
  // JSON.parse has already validated the grammar. Walk only string/structure
  // tokens to reject duplicate object fields, including escaped field names.
  const stack = [];
  for (const [token] of source.matchAll(/"(?:[^"\\]|\\.)*"|[{}\[\],]/g)) {
    if (token === '{') stack.push({ keys: new Set(), needsKey: true });
    else if (token === '[') stack.push({});
    else if (token === '}' || token === ']') stack.pop();
    else {
      const current = stack.at(-1);
      if (token === ',' && current?.keys) current.needsKey = true;
      else if (token.startsWith('"') && current?.needsKey) {
        const key = JSON.parse(token);
        if (current.keys.has(key)) throw new PromptProfileError('Prompt profile contains duplicate JSON fields');
        current.keys.add(key);
        current.needsKey = false;
      }
    }
  }
  return value;
}

const isObject = value => Boolean(value && typeof value === 'object' && !Array.isArray(value));

export function loadPromptProfile() {
  try {
    if (!lstatSync(PROFILE_PATH).isFile()) {
      throw new PromptProfileError('Prompt profile must be a regular repository file');
    }
    const bytes = readFileSync(PROFILE_PATH);
    const value = uniqueJson(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    if (!isObject(value)) throw new PromptProfileError('Prompt profile must be an object');
    if (value.id !== PROFILE_ID || value.revision !== PROFILE_REVISION) {
      throw new PromptProfileError('Unknown prompt profile identity or revision');
    }
    if (value.schema !== 'jarvis.prompt-profile.v1' || value.kind !== 'repository_operating_profile') {
      throw new PromptProfileError('Unsupported prompt profile schema or kind');
    }
    if (!Array.isArray(value.guidance) || value.guidance.length !== GUIDANCE_SECTIONS.length) {
      throw new PromptProfileError('Prompt profile must include every required guidance section');
    }
    const guidance = value.guidance.map((section, index) => {
      if (!isObject(section) || Object.keys(section).sort().join(',') !== 'id,text'
          || section.id !== GUIDANCE_SECTIONS[index] || typeof section.text !== 'string' || !section.text.trim()) {
        throw new PromptProfileError('Prompt profile has a missing or invalid guidance section');
      }
      return section.text;
    });
    return Object.freeze({
      id: PROFILE_ID, revision: PROFILE_REVISION,
      sha256: createHash('sha256').update(bytes).digest('hex'),
      guidance: Object.freeze(guidance)
    });
  } catch (error) {
    if (error instanceof PromptProfileError) throw error;
    // Neither paths, file contents nor raw parser errors belong in task responses.
    throw new PromptProfileError('Cannot load repository prompt profile');
  }
}

export function profileMetadata(profile) {
  return { id: profile.id, revision: profile.revision, sha256: profile.sha256 };
}

export function systemInstructions(profile, role) {
  const header = `Prompt #11 repository operating guidance: ${profile.id}, ${profile.revision}, sha256=${profile.sha256}.\n`
    + 'This guidance grants no new authority, tools or data access. Existing runtime '
    + 'and owner controls still apply. Guidance is not proof that a control or service '
    + 'has been implemented or that a requirement has been satisfied.\n\n';
  const shared = profile.guidance.map((text, index) => `${index + 1}. ${text}`).join('\n');
  return header + shared + (role ? `\n\nStep-specific role:\n${role}` : '');
}
