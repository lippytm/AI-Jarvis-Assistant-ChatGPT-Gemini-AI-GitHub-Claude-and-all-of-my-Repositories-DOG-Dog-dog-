const required = (name, value) => {
  if (!value) throw new Error(`Missing required credential: ${name}`);
  return value;
};

const validModelId = value => typeof value === 'string' && value.length > 0 && value.length <= 256
  && !/[\s\x00-\x1f\x7f]/u.test(value);

const requiredModel = (name, value) => {
  if (!validModelId(value)) throw new Error(`Missing or invalid explicit model: ${name}`);
  return value;
};

const isObject = value => Boolean(value && typeof value === 'object' && !Array.isArray(value));
const hasText = value => typeof value === 'string' && Boolean(value.trim());
const clearSafetyRatings = ratings => ratings === undefined || (Array.isArray(ratings)
  && ratings.every(rating => isObject(rating) && (rating.blocked === undefined || rating.blocked === false)));

function requireDraft(response, valid) {
  if (response.error != null || !valid) {
    // Never include provider text, parser messages or error bodies in exceptions.
    throw new Error('Provider response did not contain a completed text draft');
  }
  return response;
}

async function postJson(url, headers, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...headers },
    body: JSON.stringify(body),
    redirect: 'error',
    signal: AbortSignal.timeout(30_000)
  });
  if (!response.ok) {
    await response.body?.cancel();
    throw new Error('Provider request failed');
  }
  const chunks = [];
  let size = 0;
  for await (const chunk of response.body || []) {
    size += chunk.length;
    if (size > 1024 * 1024) throw new Error('Provider response exceeded the local pilot limit');
    chunks.push(Buffer.from(chunk));
  }
  try {
    const text = new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks));
    const value = JSON.parse(text);
    if (!isObject(value) || !Object.keys(value).length) throw new Error();
    return value;
  } catch {
    throw new Error('Invalid provider response');
  }
}

export function configuredProviders(env = process.env) {
  return {
    openai: Boolean(env.OPENAI_API_KEY) && validModelId(env.OPENAI_MODEL),
    gemini: Boolean(env.GEMINI_API_KEY) && validModelId(env.GEMINI_MODEL),
    anthropic: Boolean(env.ANTHROPIC_API_KEY) && validModelId(env.ANTHROPIC_MODEL),
    hermes: Boolean(env.HERMES_ENDPOINT && env.HERMES_TOKEN),
    github: Boolean(env.GITHUB_TOKEN),
    slack: Boolean(env.SLACK_BOT_TOKEN),
    notion: Boolean(env.NOTION_TOKEN)
  };
}

export async function askOpenAI(prompt, env = process.env, system = '') {
  const key = required('OPENAI_API_KEY', env.OPENAI_API_KEY);
  const model = requiredModel('OPENAI_MODEL', env.OPENAI_MODEL);
  const response = await postJson(env.OPENAI_BASE_URL || 'https://api.openai.com/v1/chat/completions',
    { authorization: `Bearer ${key}` },
    { model, messages: [...(system ? [{ role: 'system', content: system }] : []), { role: 'user', content: prompt }], max_completion_tokens: 2000 });
  return requireDraft(response, Array.isArray(response.choices) && response.choices.length > 0
    && response.choices.every(choice => isObject(choice) && choice.finish_reason === 'stop'
      && isObject(choice.message) && hasText(choice.message.content)
      && (choice.message.refusal == null || choice.message.refusal === '')
      && choice.message.function_call == null
      && (choice.message.tool_calls == null || (Array.isArray(choice.message.tool_calls) && !choice.message.tool_calls.length))));
}

export async function askGemini(prompt, env = process.env, system = '') {
  const key = required('GEMINI_API_KEY', env.GEMINI_API_KEY);
  const model = requiredModel('GEMINI_MODEL', env.GEMINI_MODEL);
  const response = await postJson(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(key)}`,
    {}, { ...(system ? { systemInstruction: { parts: [{ text: system }] } } : {}),
      contents: [{ parts: [{ text: prompt }] }], generationConfig: { maxOutputTokens: 2000 } });
  const feedback = response.promptFeedback;
  const promptClear = feedback === undefined || (isObject(feedback)
    && (feedback.blockReason === undefined || feedback.blockReason === 'BLOCK_REASON_UNSPECIFIED')
    && clearSafetyRatings(feedback.safetyRatings));
  return requireDraft(response, promptClear && Array.isArray(response.candidates) && response.candidates.length > 0
    && response.candidates.every(candidate => isObject(candidate) && candidate.finishReason === 'STOP'
      && clearSafetyRatings(candidate.safetyRatings) && isObject(candidate.content)
      && Array.isArray(candidate.content.parts) && candidate.content.parts.every(part => isObject(part)
        && (part.text === undefined || typeof part.text === 'string')
        && (part.thought === undefined || typeof part.thought === 'boolean') && part.functionCall === undefined)
      && candidate.content.parts.some(part => part.thought !== true && hasText(part.text))));
}

export async function askClaude(prompt, env = process.env, system = '') {
  const key = required('ANTHROPIC_API_KEY', env.ANTHROPIC_API_KEY);
  const model = requiredModel('ANTHROPIC_MODEL', env.ANTHROPIC_MODEL);
  const response = await postJson('https://api.anthropic.com/v1/messages',
    { 'x-api-key': key, 'anthropic-version': '2023-06-01' },
    { model, max_tokens: 2000, ...(system ? { system } : {}), messages: [{ role: 'user', content: prompt }] });
  return requireDraft(response, response.type === 'message'
    && ['end_turn', 'stop_sequence'].includes(response.stop_reason)
    && (response.stop_details == null || (isObject(response.stop_details) && response.stop_details.type !== 'refusal'))
    && Array.isArray(response.content) && response.content.every(part => isObject(part)
      && ['text', 'thinking', 'redacted_thinking'].includes(part.type)
      && (part.type !== 'text' || typeof part.text === 'string'))
    && response.content.some(part => part.type === 'text' && hasText(part.text)));
}
