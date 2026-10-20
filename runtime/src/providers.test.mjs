import assert from 'node:assert/strict';
import test from 'node:test';
import { askOpenAI, askGemini, askClaude, configuredProviders } from './providers.mjs';
import { orchestrate } from './orchestrator.mjs';

const DRAFT_TEXT = 'A completed synthetic draft.';
const RESPONSES = {
  openai: { id: 'synthetic-openai-response', choices: [{ index: 0, finish_reason: 'stop',
    message: { role: 'assistant', content: DRAFT_TEXT, refusal: null } }], usage: { completion_tokens: 6 } },
  gemini: { responseId: 'synthetic-gemini-response', candidates: [{ index: 0, finishReason: 'STOP',
    content: { role: 'model', parts: [{ text: DRAFT_TEXT }] } }], usageMetadata: { candidatesTokenCount: 6 } },
  anthropic: { id: 'synthetic-anthropic-response', type: 'message', role: 'assistant', stop_reason: 'end_turn',
    content: [{ type: 'text', text: DRAFT_TEXT }], usage: { output_tokens: 6 } }
};
const ENV = {
  OPENAI_API_KEY: 'synthetic', OPENAI_MODEL: 'operator-openai',
  GEMINI_API_KEY: 'synthetic', GEMINI_MODEL: 'operator-gemini',
  ANTHROPIC_API_KEY: 'synthetic', ANTHROPIC_MODEL: 'operator-anthropic'
};
const ADAPTERS = { openai: askOpenAI, gemini: askGemini, anthropic: askClaude };
const providerForUrl = url => url.includes('googleapis.com') ? 'gemini' : url.includes('anthropic.com') ? 'anthropic' : 'openai';
const incompleteDraft = error => error.message === 'Provider response did not contain a completed text draft';

function openaiChoice(changes) {
  return { ...RESPONSES.openai, choices: [{ ...RESPONSES.openai.choices[0], ...changes }] };
}

function geminiCandidate(changes) {
  return { ...RESPONSES.gemini, candidates: [{ ...RESPONSES.gemini.candidates[0], ...changes }] };
}

test('advisory provider requests have deadlines, output limits and no redirects', async t => {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push({ url, options, body: JSON.parse(options.body) });
    return new Response(JSON.stringify(RESPONSES[providerForUrl(url)]), { status: 200 });
  });
  for (const [provider, ask] of Object.entries(ADAPTERS)) {
    assert.deepEqual(await ask('synthetic task', ENV), RESPONSES[provider]);
  }
  assert.equal(calls.length, 3);
  for (const call of calls) {
    assert.equal(call.options.redirect, 'error');
    assert.ok(call.options.signal instanceof AbortSignal);
  }
  assert.equal(calls[0].body.max_completion_tokens, 2000);
  assert.equal(calls[0].body.model, 'operator-openai');
  assert.equal('max_tokens' in calls[0].body, false);
  assert.equal('temperature' in calls[0].body, false);
  assert.match(calls[1].url, /\/models\/operator-gemini:generateContent\?/);
  assert.equal(calls[1].body.generationConfig.maxOutputTokens, 2000);
  assert.equal(calls[2].body.model, 'operator-anthropic');
  assert.equal(calls[2].body.max_tokens, 2000);
});

test('provider configuration and direct adapters require explicit model IDs', async t => {
  let calls = 0;
  t.mock.method(globalThis, 'fetch', async () => { calls++; throw new Error('must not fetch'); });
  for (const [provider, key, model, ask] of [
    ['openai', 'OPENAI_API_KEY', 'OPENAI_MODEL', askOpenAI],
    ['gemini', 'GEMINI_API_KEY', 'GEMINI_MODEL', askGemini],
    ['anthropic', 'ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL', askClaude]
  ]) {
    assert.equal(configuredProviders({ [key]: 'synthetic' })[provider], false);
    assert.equal(configuredProviders({ [model]: 'operator-model' })[provider], false);
    assert.equal(configuredProviders({ [key]: 'synthetic', [model]: 'operator-model' })[provider], true);
    for (const value of [undefined, '', ' ', 'bad\nmodel']) {
      await assert.rejects(ask('synthetic task', { [key]: 'synthetic', [model]: value }), /explicit model/);
    }
  }
  assert.equal(calls, 0);
});

test('provider error bodies are not included in thrown errors', async t => {
  t.mock.method(globalThis, 'fetch', async () => new Response('private-provider-value', { status: 401 }));
  await assert.rejects(askOpenAI('synthetic', { OPENAI_API_KEY: 'synthetic', OPENAI_MODEL: 'operator-model' }),
    error => error.message === 'Provider request failed');
});

test('oversized provider responses fail instead of being retained', async t => {
  t.mock.method(globalThis, 'fetch', async () => new Response('x'.repeat(1024 * 1024 + 1)));
  await assert.rejects(askOpenAI('synthetic', { OPENAI_API_KEY: 'synthetic', OPENAI_MODEL: 'operator-model' }), /exceeded/);
});

test('successful HTTP responses must contain a nonempty strict UTF-8 JSON object', async t => {
  let responseBody;
  t.mock.method(globalThis, 'fetch', async () => new Response(responseBody, { status: 200 }));
  for (const [provider, ask] of Object.entries(ADAPTERS)) {
    const encoded = JSON.stringify(RESPONSES[provider]);
    const position = encoded.indexOf(DRAFT_TEXT);
    const invalidUtf8 = Buffer.concat([Buffer.from(encoded.slice(0, position)), Buffer.from([0xff]),
      Buffer.from(encoded.slice(position + DRAFT_TEXT.length))]);
    for (const bad of ['', ' \n ', 'null', '[]', 'true', '"text"', '{}', '{"private-value":', invalidUtf8]) {
      responseBody = bad;
      await assert.rejects(ask('synthetic task', ENV), error => error.message === 'Invalid provider response');
    }
  }
});

test('OpenAI requires completed nonempty text with no refusal or pending tool call', async t => {
  let responseBody;
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(responseBody), { status: 200 }));
  const invalid = [
    { choices: [] }, { choices: null }, { choices: [null] },
    ...[undefined, null, '', ' ', 42, []].map(content => openaiChoice({ message: { content } })),
    ...[undefined, 'length', 'content_filter', 'tool_calls', 'function_call', 'unknown'].map(finish_reason => openaiChoice({ finish_reason })),
    openaiChoice({ message: { ...RESPONSES.openai.choices[0].message, refusal: 'private-refusal-value' } }),
    openaiChoice({ message: { ...RESPONSES.openai.choices[0].message, tool_calls: [{ type: 'function' }] } }),
    { ...RESPONSES.openai, error: { message: 'private-provider-value' } },
    { choices: [...RESPONSES.openai.choices, { ...RESPONSES.openai.choices[0], finish_reason: 'length' }] }
  ];
  for (responseBody of invalid) await assert.rejects(askOpenAI('synthetic task', ENV), incompleteDraft);
});

test('Gemini requires completed answer text and rejects blocked or thought-only candidates', async t => {
  let responseBody;
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(responseBody), { status: 200 }));
  const invalid = [
    { candidates: [] }, { candidates: null }, { candidates: [null] },
    ...[null, [], [null], [{ text: ' ' }], [{ text: 42 }], [{ text: DRAFT_TEXT, thought: true }],
      [{ functionCall: { name: 'synthetic-tool' } }]].map(parts => geminiCandidate({ content: { parts } })),
    ...[undefined, 'MAX_TOKENS', 'SAFETY', 'RECITATION', 'CONTINUATION', 'UNKNOWN'].map(finishReason => geminiCandidate({ finishReason })),
    { ...RESPONSES.gemini, promptFeedback: { blockReason: 'SAFETY' } },
    { ...RESPONSES.gemini, promptFeedback: { safetyRatings: [{ blocked: true }] } },
    geminiCandidate({ safetyRatings: [{ blocked: true }] }),
    { ...RESPONSES.gemini, error: { message: 'private-provider-value' } },
    { candidates: [...RESPONSES.gemini.candidates, { ...RESPONSES.gemini.candidates[0], finishReason: 'MAX_TOKENS' }] }
  ];
  for (responseBody of invalid) await assert.rejects(askGemini('synthetic task', ENV), incompleteDraft);
});

test('Anthropic requires completed answer text and rejects refusal details even on end_turn', async t => {
  let responseBody;
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(responseBody), { status: 200 }));
  const invalid = [
    ...[undefined, null, [], [null], [{ type: 'text', text: ' ' }], [{ type: 'text', text: 42 }],
      [{ type: 'thinking', thinking: 'not a final answer' }], [{ type: 'tool_use', text: DRAFT_TEXT }]]
      .map(content => ({ ...RESPONSES.anthropic, content })),
    ...[undefined, 'max_tokens', 'model_context_window_exceeded', 'pause_turn', 'tool_use', 'refusal', 'unknown']
      .map(stop_reason => ({ ...RESPONSES.anthropic, stop_reason })),
    { ...RESPONSES.anthropic, type: 'error' },
    { ...RESPONSES.anthropic, stop_details: { type: 'refusal', explanation: 'private-refusal-value' } },
    { ...RESPONSES.anthropic, error: { message: 'private-provider-value' } }
  ];
  for (responseBody of invalid) await assert.rejects(askClaude('synthetic task', ENV), incompleteDraft);
  responseBody = { ...RESPONSES.anthropic, stop_reason: 'stop_sequence', stop_sequence: 'synthetic-stop' };
  assert.deepEqual(await askClaude('synthetic task', ENV), responseBody);
});

test('a bad native provider response cannot become an orchestrator draft_ready result', async t => {
  let badProvider, badBody;
  t.mock.method(globalThis, 'fetch', async url => {
    const provider = providerForUrl(url);
    return new Response(provider === badProvider ? badBody : JSON.stringify(RESPONSES[provider]), { status: 200 });
  });
  const env = { ...ENV, JARVIS_PILOT_REPOSITORY: 'example/pilot', JARVIS_DRY_RUN: 'false', JARVIS_ALLOW_EXTERNAL: 'true' };
  const truncated = {
    openai: openaiChoice({ finish_reason: 'length' }),
    gemini: geminiCandidate({ finishReason: 'MAX_TOKENS' }),
    anthropic: { ...RESPONSES.anthropic, stop_reason: 'max_tokens' }
  };
  for (badProvider of Object.keys(ADAPTERS)) {
    for (badBody of ['', 'null', '{"error":{"message":"private-provider-value"}}', JSON.stringify(truncated[badProvider])]) {
      await assert.rejects(orchestrate({ task: 'Review the supplied description.' }, env),
        error => error.status === 502 && error.code === 'provider_request_failed' && error.message === 'provider_request_failed');
    }
  }
});
