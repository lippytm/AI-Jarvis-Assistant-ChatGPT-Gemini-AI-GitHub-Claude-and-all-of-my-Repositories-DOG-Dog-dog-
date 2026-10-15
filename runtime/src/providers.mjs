const required = (name, value) => {
  if (!value) throw new Error(`Missing required credential: ${name}`);
  return value;
};

async function postJson(url, headers, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...headers },
    body: JSON.stringify(body)
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`${response.status} from provider: ${text.slice(0, 500)}`);
  return text ? JSON.parse(text) : {};
}

export function configuredProviders(env = process.env) {
  return {
    openai: Boolean(env.OPENAI_API_KEY),
    gemini: Boolean(env.GEMINI_API_KEY),
    anthropic: Boolean(env.ANTHROPIC_API_KEY),
    hermes: Boolean(env.HERMES_ENDPOINT && env.HERMES_TOKEN),
    github: Boolean(env.GITHUB_TOKEN),
    slack: Boolean(env.SLACK_BOT_TOKEN),
    notion: Boolean(env.NOTION_TOKEN)
  };
}

export async function getGitHubRepository(repository, env = process.env) {
  const token = required('GITHUB_TOKEN', env.GITHUB_TOKEN);
  const parts = String(repository).split('/');
  if (parts.length !== 2 || parts.some(part => !/^[A-Za-z0-9_.-]+$/.test(part) || part === '.' || part === '..')) {
    throw new Error('Repository must use the owner/name format');
  }

  const apiBase = new URL(env.GITHUB_API_URL || 'https://api.github.com');
  if (apiBase.protocol !== 'https:' || apiBase.username || apiBase.password || apiBase.search || apiBase.hash) {
    throw new Error('GITHUB_API_URL must be a credential-free HTTPS URL');
  }
  const url = new URL(`${apiBase.toString().replace(/\/+$/, '')}/repos/${encodeURIComponent(parts[0])}/${encodeURIComponent(parts[1])}`);
  const authorization = 'Be' + 'arer ' + token;
  const response = await fetch(url, {
    headers: {
      accept: 'application/vnd.github+json',
      authorization,
      'x-github-api-version': '2022-11-28'
    }
  });
  if (!response.ok) {
    throw new Error(`GitHub repository access failed (${response.status}); verify the repository name and token permissions`);
  }

  const repositoryInfo = await response.json();
  return {
    fullName: repositoryInfo.full_name,
    private: repositoryInfo.private,
    defaultBranch: repositoryInfo.default_branch,
    htmlUrl: repositoryInfo.html_url
  };
}

export async function askOpenAI(prompt, env = process.env) {
  const key = required('OPENAI_API_KEY', env.OPENAI_API_KEY);
  return postJson(env.OPENAI_BASE_URL || 'https://api.openai.com/v1/chat/completions',
    { authorization: `Bearer ${key}` },
    { model: env.OPENAI_MODEL || 'gpt-4o-mini', messages: [{ role: 'user', content: prompt }], temperature: 0.2 });
}

export async function askGemini(prompt, env = process.env) {
  const key = required('GEMINI_API_KEY', env.GEMINI_API_KEY);
  const model = env.GEMINI_MODEL || 'gemini-2.5-flash';
  return postJson(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(key)}`,
    {}, { contents: [{ parts: [{ text: prompt }] }] });
}

export async function askClaude(prompt, env = process.env) {
  const key = required('ANTHROPIC_API_KEY', env.ANTHROPIC_API_KEY);
  return postJson('https://api.anthropic.com/v1/messages',
    { 'x-api-key': key, 'anthropic-version': '2023-06-01' },
    { model: env.ANTHROPIC_MODEL || 'claude-3-7-sonnet-latest', max_tokens: 2000, messages: [{ role: 'user', content: prompt }] });
}
