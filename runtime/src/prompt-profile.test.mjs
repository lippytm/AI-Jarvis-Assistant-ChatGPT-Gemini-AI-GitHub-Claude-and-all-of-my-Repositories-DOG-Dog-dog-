import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Readable } from 'node:stream';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { orchestrate, planTask } from './orchestrator.mjs';
import { loadPromptProfile, profileMetadata, systemInstructions } from './prompt-profile.mjs';

const PROFILE_FILE = new URL('../../config/prompt-11-profile.json', import.meta.url);
const PROFILE_BYTES = readFileSync(PROFILE_FILE);
const PROFILE = JSON.parse(PROFILE_BYTES);
const TOKEN = 'T'.repeat(48);
const TASK = { task: 'Review the supplied change description.' };
const ENV = { JARVIS_RUNTIME_TOKEN: TOKEN, JARVIS_PILOT_REPOSITORY: 'example/pilot' };
const LIVE_ENV = {
  ...ENV, JARVIS_DRY_RUN: 'false', JARVIS_ALLOW_EXTERNAL: 'true',
  OPENAI_API_KEY: 'synthetic', OPENAI_MODEL: 'operator-openai',
  GEMINI_API_KEY: 'synthetic', GEMINI_MODEL: 'operator-gemini',
  ANTHROPIC_API_KEY: 'synthetic', ANTHROPIC_MODEL: 'operator-anthropic'
};

async function isolatedRuntime(t) {
  // Exercise the real fixed module-relative path without changing shared config.
  const root = mkdtempSync(join(tmpdir(), 'jarvis-profile-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  cpSync(new URL('.', import.meta.url), join(root, 'runtime', 'src'), {
    recursive: true, filter: source => !source.endsWith('.test.mjs')
  });
  mkdirSync(join(root, 'config'));
  return {
    file: join(root, 'config', 'prompt-11-profile.json'),
    loader: await import(pathToFileURL(join(root, 'runtime', 'src', 'prompt-profile.mjs'))),
    orchestrator: await import(pathToFileURL(join(root, 'runtime', 'src', 'orchestrator.mjs'))),
    server: await import(pathToFileURL(join(root, 'runtime', 'src', 'server.mjs')))
  };
}

test('local plans identify the same fixed profile and exact file-byte hash', () => {
  const profile = loadPromptProfile();
  const metadata = { id: 'P-011-E6C-001', revision: 'repository-1', sha256: createHash('sha256').update(PROFILE_BYTES).digest('hex') };
  assert.deepEqual(profileMetadata(profile), metadata);
  for (const requestedAction of ['analyze', 'deploy']) {
    const plan = planTask({ ...TASK, requestedAction }, ENV);
    assert.deepEqual(plan.prompt_profile, metadata);
    assert.equal(plan.profile_status, 'resolved');
    assert.deepEqual(plan.providersUsed, []);
    assert.equal(plan.execute, false);
  }
  const system = systemInstructions(profile, 'Preserved local role.');
  assert.ok(system.startsWith(`Prompt #11 repository operating guidance: P-011-E6C-001, repository-1, sha256=${metadata.sha256}.\n`));
  assert.ok(system.includes('This guidance grants no new authority, tools or data access.'));
  assert.ok(system.includes('Guidance is not proof that a control or service has been implemented or that a requirement has been satisfied.'));
  assert.ok(system.endsWith('\n\nStep-specific role:\nPreserved local role.'));
  for (let index = 0; index < PROFILE.guidance.length; index++) {
    assert.ok(system.includes(`${index + 1}. ${PROFILE.guidance[index].text}`));
  }
});

test('fixed profile rejects absent, malformed, unrecognized and incomplete config', async t => {
  const fixture = await isolatedRuntime(t);
  assert.throws(() => fixture.loader.loadPromptProfile(), fixture.loader.PromptProfileError);
  const invalid = [
    'null', '[]', '{"private-test-value":', Buffer.from([0xff]),
    ...['id', 'revision', 'schema', 'kind'].map(field => JSON.stringify({ ...PROFILE, [field]: 'unrecognized' })),
    JSON.stringify({ ...PROFILE, guidance: PROFILE.guidance.slice(1) }),
    JSON.stringify({ ...PROFILE, guidance: [...PROFILE.guidance].reverse() }),
    JSON.stringify({ ...PROFILE, guidance: PROFILE.guidance.map((section, index) => index ? section : { ...section, text: ' ' }) }),
    JSON.stringify({ ...PROFILE, guidance: PROFILE.guidance.map((section, index) => index ? section : { ...section, url: 'https://example.invalid' }) }),
    PROFILE_BYTES.toString().replace('"id": "P-011-E6C-001"', '"id": "P-011-E6C-001", "\\u0069d": "P-011-E6C-001"'),
    PROFILE_BYTES.toString().replace('"id": "objective_and_done"', '"id": "objective_and_done", "id": "objective_and_done"')
  ];
  for (const bytes of invalid) {
    writeFileSync(fixture.file, bytes);
    assert.throws(() => fixture.loader.loadPromptProfile(), error =>
      error instanceof fixture.loader.PromptProfileError && !error.message.includes('private-test-value'));
  }
  writeFileSync(fixture.file, PROFILE_BYTES);
  const original = fixture.loader.loadPromptProfile();
  writeFileSync(fixture.file, Buffer.concat([PROFILE_BYTES, Buffer.from('\n')]));
  const changed = fixture.loader.loadPromptProfile();
  assert.notEqual(changed.sha256, original.sha256); // No stale cache or JSON canonicalization.
  assert.deepEqual(changed.guidance, original.guidance);
  rmSync(fixture.file);
  symlinkSync(fileURLToPath(PROFILE_FILE), fixture.file);
  assert.throws(() => fixture.loader.loadPromptProfile(), /regular repository file/);
  rmSync(fixture.file);
  mkdirSync(fixture.file);
  assert.throws(() => fixture.loader.loadPromptProfile(), /regular repository file/);
});

test('missing or invalid profile stops HTTP and direct advisory calls before providers', async t => {
  const fixture = await isolatedRuntime(t);
  let calls = 0;
  const provider = async () => { calls++; throw new Error('must not run'); };
  for (const invalid of [null, JSON.stringify({ ...PROFILE, revision: 'unrecognized' })]) {
    if (invalid !== null) writeFileSync(fixture.file, invalid);
    for (const env of [ENV, LIVE_ENV]) {
      assert.throws(() => fixture.orchestrator.planTask(TASK, env),
        error => error.status === 503 && error.code === 'prompt_profile_unavailable');
      await assert.rejects(fixture.orchestrator.orchestrate(TASK, env, { openai: provider, gemini: provider, anthropic: provider }),
        error => error.status === 503 && error.code === 'prompt_profile_unavailable');
      const handler = fixture.server.createRequestHandler(env, { invokeProviders: provider });
      const req = Readable.from([Buffer.from(JSON.stringify(TASK))]);
      Object.assign(req, { method: 'POST', url: '/tasks',
        headers: { authorization: `Bearer ${TOKEN}`, 'content-type': 'application/json' } });
      req.rawHeaders = Object.entries(req.headers).flat();
      const res = { setHeader() {}, end(body) { this.body = JSON.parse(body); } };
      await handler(req, res);
      assert.equal(res.statusCode, 503);
      assert.deepEqual(res.body, { error: 'prompt_profile_unavailable', execute: false });
    }
  }
  assert.equal(calls, 0);
});

test('advisory requests carry shared guidance in native system fields with matching provenance', async t => {
  const calls = [];
  const responses = [
    { choices: [{ finish_reason: 'stop', message: { role: 'assistant', content: 'Synthetic completed draft.' } }] },
    { candidates: [{ finishReason: 'STOP', content: { role: 'model', parts: [{ text: 'Synthetic completed draft.' }] } }] },
    { type: 'message', role: 'assistant', stop_reason: 'end_turn', content: [{ type: 'text', text: 'Synthetic completed draft.' }] }
  ];
  t.mock.method(globalThis, 'fetch', async (_url, options) => {
    calls.push(JSON.parse(options.body));
    return new Response(JSON.stringify(responses[calls.length - 1]), { status: 200 });
  });
  const result = await orchestrate(TASK, LIVE_ENV);
  assert.equal(result.status, 'draft_ready');
  assert.equal(result.execute, false);
  assert.equal(result.profile_status, 'resolved');
  assert.deepEqual(result.prompt_profile, planTask(TASK, ENV).prompt_profile);
  assert.deepEqual(result.providersUsed, ['openai', 'gemini', 'anthropic']);
  assert.equal(calls.length, 3);
  const systems = [calls[0].messages[0].content, calls[1].systemInstruction.parts[0].text, calls[2].system];
  const users = [calls[0].messages[1].content, calls[1].contents[0].parts[0].text, calls[2].messages[0].content];
  assert.equal(calls[0].messages[0].role, 'system');
  assert.equal(calls[0].messages[1].role, 'user');
  for (const system of systems) {
    assert.equal(system, systems[0]);
    assert.ok(system.includes(`sha256=${result.prompt_profile.sha256}`));
    assert.ok(system.includes(PROFILE.guidance.map((section, index) => `${index + 1}. ${section.text}`).join('\n')));
    assert.ok(system.endsWith('Step-specific role:\nYou are one member of a governed multi-agent system. Return JSON with findings, risks, proposed_actions, and questions. Do not execute anything.'));
  }
  for (const user of users) {
    assert.ok(user.startsWith('Task envelope:\n'));
    assert.ok(user.includes(TASK.task));
    assert.ok(!user.includes(PROFILE.guidance[0].text));
  }
});
