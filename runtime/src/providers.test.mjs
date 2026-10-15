import assert from 'node:assert/strict';
import { orchestrate } from './orchestrator.mjs';
import { getGitHubRepository } from './providers.mjs';

const originalFetch = globalThis.fetch;

try {
  let request;
  globalThis.fetch = async (url, options) => {
    request = { url: String(url), options };
    return {
      ok: true,
      json: async () => ({
        full_name: 'lippytm/example',
        private: true,
        default_branch: 'main',
        html_url: 'https://github.com/lippytm/example'
      })
    };
  };

  assert.deepEqual(await getGitHubRepository('lippytm/example', { GITHUB_TOKEN: 'test-token' }), {
    fullName: 'lippytm/example',
    private: true,
    defaultBranch: 'main',
    htmlUrl: 'https://github.com/lippytm/example'
  });
  assert.equal(request.url, 'https://api.github.com/repos/lippytm/example');
  assert.equal(request.options.headers.authorization, 'Be' + 'arer test-token');
  assert.equal(request.options.headers['x-github-api-version'], '2022-11-28');

  await assert.rejects(
    getGitHubRepository('lippytm/example', {}),
    /Missing required credential: GITHUB_TOKEN/
  );
  await assert.rejects(
    getGitHubRepository('lippytm/example/extra', { GITHUB_TOKEN: 'test-token' }),
    /owner\/name format/
  );

  globalThis.fetch = async () => ({ ok: false, status: 404 });
  await assert.rejects(
    getGitHubRepository('lippytm/private-repo', { GITHUB_TOKEN: 'test-token' }),
    /GitHub repository access failed \(404\)/
  );

  await assert.rejects(
    getGitHubRepository('lippytm/example', {
      GITHUB_TOKEN: 'test-token',
      GITHUB_API_URL: 'http://api.github.com'
    }),
    /credential-free HTTPS URL/
  );

  globalThis.fetch = async (url, options) => {
    if (String(url) === 'https://api.github.com/repos/lippytm/example') {
      return {
        ok: true,
        json: async () => ({
          full_name: 'lippytm/example',
          private: true,
          default_branch: 'main',
          html_url: 'https://github.com/lippytm/example'
        })
      };
    }
    assert.equal(options.method, 'POST');
    return { ok: true, text: async () => JSON.stringify({ choices: [] }) };
  };
  const result = await orchestrate(
    { task: 'Check repository connectivity', repository: 'lippytm/example' },
    {
      OPENAI_API_KEY: 'test-openai-key',
      GITHUB_TOKEN: 'test-token',
      JARVIS_PILOT_REPOSITORY: 'lippytm/example'
    }
  );
  assert.deepEqual(result.providersUsed.sort(), ['github', 'openai']);
  assert.equal(result.results.github.fullName, 'lippytm/example');

  await assert.rejects(
    orchestrate(
      { task: 'Check repository connectivity', repository: 'lippytm/other' },
      { OPENAI_API_KEY: 'test-openai-key', JARVIS_PILOT_REPOSITORY: 'lippytm/example' }
    ),
    /Pilot mode refuses repositories/
  );

  console.log('GitHub provider checks passed');
} finally {
  globalThis.fetch = originalFetch;
}
