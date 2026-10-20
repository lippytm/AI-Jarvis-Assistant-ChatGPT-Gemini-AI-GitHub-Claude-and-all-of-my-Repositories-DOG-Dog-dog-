import assert from 'node:assert/strict';
import { Readable } from 'node:stream';
import test from 'node:test';
import { createRequestHandler, createRuntimeServer, MAX_BODY_BYTES, runtimeConfig } from './server.mjs';
import { createEnvelope, orchestrate, planTask } from './orchestrator.mjs';
import { planQuickAction } from './quick-actions-runner.mjs';

const TOKEN = 'T'.repeat(48); // Synthetic runtime-only test token.
const ENV = { JARVIS_RUNTIME_TOKEN: TOKEN, JARVIS_PILOT_REPOSITORY: 'example/pilot' };
const TASK = { task: 'Review the supplied change description.' };

async function request(handler, payload = TASK, options = {}) {
  const chunks = options.chunks || [Buffer.from(options.raw ?? JSON.stringify(payload))];
  const req = Readable.from(chunks);
  req.method = options.method || 'POST';
  req.url = options.url || '/tasks';
  req.headers = { authorization: `Bearer ${TOKEN}`, 'content-type': 'application/json', ...options.headers };
  req.rawHeaders = options.rawHeaders || Object.entries(req.headers).filter(([, value]) => value !== undefined).flat();
  const res = {
    headers: {}, statusCode: 200, destroyed: false, writableEnded: false,
    setHeader(name, value) { this.headers[name] = value; },
    end(text) { this.text = text; this.body = JSON.parse(text); this.writableEnded = true; }
  };
  await handler(req, res);
  return res;
}

test('default configuration binds loopback and opts out of provider invocation', () => {
  const config = runtimeConfig({});
  assert.equal(config.host, '127.0.0.1');
  assert.equal(config.dryRun, true);
  assert.equal(config.allowExternal, false);
  assert.throws(() => runtimeConfig({ JARVIS_HOST: '0.0.0.0' }), /loopback/);
  assert.throws(() => runtimeConfig({ JARVIS_RUNTIME_TOKEN: 'short' }), /32/);
  assert.throws(() => runtimeConfig({ JARVIS_DRY_RUN: 'FALSE' }), /Invalid/);
  const server = createRuntimeServer({});
  assert.equal(server.listening, false); // Importing/building the server opens no socket.
  assert.equal(server.requestTimeout, 15_000);
});

test('health reveals configuration state without token or provider secrets', async () => {
  const res = await request(createRequestHandler({ ...ENV, OPENAI_API_KEY: 'private-provider-value' }), null,
    { method: 'GET', url: '/health', headers: { authorization: undefined } });
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.mode, 'local_pilot');
  assert.equal(res.body.dryRun, true);
  assert.ok(!res.text.includes(TOKEN));
  assert.ok(!res.text.includes('private-provider-value'));
});

test('dry-run never calls orchestration even when all providers are configured', async () => {
  let calls = 0;
  const handler = createRequestHandler({ ...ENV, OPENAI_API_KEY: 'fake', GEMINI_API_KEY: 'fake', ANTHROPIC_API_KEY: 'fake' }, {
    invokeProviders: async () => { calls++; throw new Error('must not run'); }
  });
  const res = await request(handler);
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.status, 'dry_run');
  assert.deepEqual(res.body.providersUsed, []);
  assert.equal(res.body.execute, false);
  assert.equal(res.body.envelope.repository, 'example/pilot');
  assert.equal(calls, 0);
});

test('missing token or repository configuration fails closed', async () => {
  for (const env of [{}, { JARVIS_RUNTIME_TOKEN: TOKEN }, { JARVIS_PILOT_REPOSITORY: 'example/pilot' }]) {
    const res = await request(createRequestHandler(env));
    assert.equal(res.statusCode, 503);
    assert.equal(res.body.error, 'runtime_not_configured');
  }
});

test('absent, wrong and duplicate authorization are denied', async () => {
  const handler = createRequestHandler(ENV);
  for (const authorization of [undefined, `Bearer ${'X'.repeat(48)}`, 'Basic credentials']) {
    const res = await request(handler, TASK, { headers: { authorization } });
    assert.equal(res.statusCode, 401);
    assert.equal(res.body.execute, false);
  }
  const duplicated = await request(handler, TASK, {
    rawHeaders: ['Authorization', `Bearer ${TOKEN}`, 'Authorization', `Bearer ${TOKEN}`]
  });
  assert.equal(duplicated.statusCode, 401);
});

test('token cannot authorize a task outside its configured repository', async () => {
  const res = await request(createRequestHandler(ENV), { ...TASK, repository: 'example/other' });
  assert.equal(res.statusCode, 403);
  assert.equal(res.body.error, 'repository_outside_pilot_scope');
});

test('provider calls need both external opt-in and disabled dry-run', async () => {
  let calls = 0;
  const dependencies = { invokeProviders: async () => { calls++; return { status: 'draft_ready' }; } };
  const stillDry = await request(createRequestHandler({ ...ENV, JARVIS_ALLOW_EXTERNAL: 'true' }, dependencies));
  assert.equal(stillDry.body.status, 'dry_run');
  const blocked = await request(createRequestHandler({ ...ENV, JARVIS_DRY_RUN: 'false' }, dependencies));
  assert.equal(blocked.statusCode, 403);
  assert.equal(calls, 0);
  const allowed = await request(createRequestHandler({ ...ENV, JARVIS_DRY_RUN: 'false', JARVIS_ALLOW_EXTERNAL: 'true' }, dependencies));
  assert.equal(allowed.statusCode, 200);
  assert.equal(allowed.body.execute, false);
  assert.equal(calls, 1); // Stub invocation only; no provider or network is used.
});

test('high-impact actions stop before provider calls, including Quick Action aliases', async () => {
  let calls = 0;
  const handler = createRequestHandler({ ...ENV, JARVIS_DRY_RUN: 'false', JARVIS_ALLOW_EXTERNAL: 'true' }, {
    invokeProviders: async () => { calls++; }
  });
  for (const requestedAction of ['deploy', 'merge', 'merge_pull_request', 'notify_slack', 'delete_resource', 'change_secret']) {
    const res = await request(handler, { ...TASK, requestedAction });
    assert.equal(res.body.status, 'approval_required');
    assert.equal(res.body.execute, false);
  }
  const suppliedApproval = await request(handler, { ...TASK, requestedAction: 'deploy', approved: true });
  assert.equal(suppliedApproval.statusCode, 400);
  assert.equal(calls, 0);
});

test('JSON input fields and sizes are validated before invoking providers', async () => {
  const handler = createRequestHandler(ENV);
  for (const payload of [null, [], 'task', {}, { task: 42 }, { task: ' ' },
    { task: 'x'.repeat(8001) }, { ...TASK, files: [42] }, { ...TASK, files: Array(65).fill('file') },
    { ...TASK, repository: '../other' }, { ...TASK, requestedAction: 'execute_shell' }, { ...TASK, extra: 'x' }]) {
    const res = await request(handler, payload);
    assert.equal(res.statusCode, 400);
    assert.equal(res.body.execute, false);
  }
});

test('malformed JSON and invalid UTF-8 return a static error', async () => {
  const handler = createRequestHandler(ENV);
  for (const options of [{ raw: '{"private-value":' }, { chunks: [Buffer.from([0xff])] }]) {
    const res = await request(handler, TASK, options);
    assert.equal(res.statusCode, 400);
    assert.equal(res.body.error, 'invalid_json');
    assert.ok(!res.text.includes('private-value'));
  }
});

test('JSON content type and identity content encoding are required', async () => {
  const handler = createRequestHandler(ENV);
  for (const headers of [{ 'content-type': 'text/plain' }, { 'content-encoding': 'gzip' }]) {
    assert.equal((await request(handler, TASK, { headers })).statusCode, 415);
  }
});

test('declared and streamed oversized bodies fail without buffering the entire request', async () => {
  const handler = createRequestHandler(ENV);
  assert.equal((await request(handler, TASK, { headers: { 'content-length': String(MAX_BODY_BYTES + 1) } })).statusCode, 413);
  const streamed = await request(handler, TASK, {
    chunks: [Buffer.alloc(MAX_BODY_BYTES / 2), Buffer.alloc(MAX_BODY_BYTES / 2 + 1)]
  });
  assert.equal(streamed.statusCode, 413);
  assert.equal(streamed.body.error, 'request_body_too_large');
});

test('unexpected provider errors do not expose secrets or raw bodies', async () => {
  const handler = createRequestHandler({ ...ENV, JARVIS_DRY_RUN: 'false', JARVIS_ALLOW_EXTERNAL: 'true' }, {
    invokeProviders: async () => { throw new Error('private-provider-value'); }
  });
  const res = await request(handler);
  assert.equal(res.statusCode, 502);
  assert.equal(res.body.error, 'request_failed');
  assert.ok(!res.text.includes('private-provider-value'));
});

test('only one provider task runs at once and its slot is released', async () => {
  let release, entered;
  const started = new Promise(resolve => { entered = resolve; });
  const finished = new Promise(resolve => { release = resolve; });
  const handler = createRequestHandler({ ...ENV, JARVIS_DRY_RUN: 'false', JARVIS_ALLOW_EXTERNAL: 'true' }, {
    invokeProviders: async () => { entered(); await finished; return { status: 'draft_ready' }; }
  });
  const first = request(handler);
  await started;
  assert.equal((await request(handler)).statusCode, 429);
  release();
  assert.equal((await first).statusCode, 200);
  assert.equal((await request(handler)).statusCode, 200);
});

test('orchestrator API itself cannot bypass dry-run and external opt-in', async () => {
  let calls = 0;
  const providers = { openai: async () => { calls++; return { draft: 'synthetic' }; } };
  const env = { ...ENV, OPENAI_API_KEY: 'fake' };
  assert.equal((await orchestrate(TASK, env, providers)).status, 'dry_run');
  await assert.rejects(orchestrate(TASK, { ...env, JARVIS_DRY_RUN: 'false' }, providers), /external_invocation_disabled/);
  assert.equal(calls, 0);
  const liveOptions = { ...env, JARVIS_DRY_RUN: 'false', JARVIS_ALLOW_EXTERNAL: 'true' };
  assert.equal((await orchestrate({ ...TASK, requestedAction: 'deploy' }, liveOptions, providers)).status, 'approval_required');
  assert.equal(calls, 0);
  const result = await orchestrate(TASK, liveOptions, providers);
  assert.equal(result.status, 'draft_ready');
  assert.equal(result.execute, false);
  assert.equal(calls, 1);
});

test('missing provider credentials and provider failure cannot look successful', async () => {
  const env = { ...ENV, JARVIS_DRY_RUN: 'false', JARVIS_ALLOW_EXTERNAL: 'true' };
  await assert.rejects(orchestrate(TASK, env), /provider_credentials_not_configured/);
  await assert.rejects(orchestrate(TASK, { ...env, OPENAI_API_KEY: 'fake' }, {
    openai: async () => { throw new Error('private-provider-value'); }
  }), error => error.code === 'provider_request_failed' && !error.message.includes('private-provider-value'));
});

test('a provider failure waits for other started providers before finishing', async () => {
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  const result = orchestrate(TASK, {
    ...ENV, JARVIS_DRY_RUN: 'false', JARVIS_ALLOW_EXTERNAL: 'true', OPENAI_API_KEY: 'fake', GEMINI_API_KEY: 'fake'
  }, {
    openai: async () => { throw new Error('synthetic failure'); },
    gemini: async () => { await pending; return { draft: 'synthetic' }; }
  });
  let settled = false;
  result.catch(() => { settled = true; });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(settled, false);
  release();
  await assert.rejects(result, /provider_request_failed/);
});

test('envelope and Quick Action plans remain non-executing and cannot self-approve', () => {
  assert.equal(createEnvelope(TASK).task, TASK.task);
  assert.throws(() => planTask(TASK, {}), /pilot_repository_not_configured/);
  const plan = planQuickAction({ action: 'deploy', repository: 'example/pilot', approved: true }, ENV);
  assert.equal(plan.execute, false);
  assert.equal(plan.decision.allowed, false);
  assert.equal(plan.decision.status, 'approval_required');
});
