import assert from 'node:assert/strict';
import test from 'node:test';
import { askOpenAI, askGemini, askClaude } from './providers.mjs';

test('advisory provider requests have deadlines, output limits and no redirects', async t => {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push({ url, options, body: JSON.parse(options.body) });
    return new Response('{"synthetic":true}', { status: 200 });
  });
  const env = { OPENAI_API_KEY: 'synthetic', GEMINI_API_KEY: 'synthetic', ANTHROPIC_API_KEY: 'synthetic' };
  await askOpenAI('synthetic task', env);
  await askGemini('synthetic task', env);
  await askClaude('synthetic task', env);
  assert.equal(calls.length, 3);
  for (const call of calls) {
    assert.equal(call.options.redirect, 'error');
    assert.ok(call.options.signal instanceof AbortSignal);
  }
  assert.equal(calls[0].body.max_tokens, 2000);
  assert.equal(calls[1].body.generationConfig.maxOutputTokens, 2000);
  assert.equal(calls[2].body.max_tokens, 2000);
});

test('provider error bodies are not included in thrown errors', async t => {
  t.mock.method(globalThis, 'fetch', async () => new Response('private-provider-value', { status: 401 }));
  await assert.rejects(askOpenAI('synthetic', { OPENAI_API_KEY: 'synthetic' }),
    error => error.message === 'Provider request failed');
});

test('oversized provider responses fail instead of being retained', async t => {
  t.mock.method(globalThis, 'fetch', async () => new Response('x'.repeat(1024 * 1024 + 1)));
  await assert.rejects(askOpenAI('synthetic', { OPENAI_API_KEY: 'synthetic' }), /exceeded/);
});
