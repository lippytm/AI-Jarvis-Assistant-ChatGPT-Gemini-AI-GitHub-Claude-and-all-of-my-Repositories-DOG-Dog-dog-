import http from 'node:http';
import { createHash, timingSafeEqual } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { orchestrate, planTask, RuntimeError, validRepository } from './orchestrator.mjs';

export const MAX_BODY_BYTES = 32 * 1024;
const tokenPattern = /^[A-Za-z0-9_-]{32,256}$/;

export function runtimeConfig(env = process.env) {
  const host = env.JARVIS_HOST || '127.0.0.1';
  // This is a local pilot. Public serving needs a separate authenticated TLS deployment.
  if (!['127.0.0.1', '::1'].includes(host)) throw new Error('JARVIS_HOST must be a loopback address');
  const port = Number(env.JARVIS_PORT || 8787);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid JARVIS_PORT');
  for (const name of ['JARVIS_DRY_RUN', 'JARVIS_ALLOW_EXTERNAL']) {
    if (env[name] && !['true', 'false'].includes(env[name])) throw new Error(`Invalid ${name}`);
  }
  const token = env.JARVIS_RUNTIME_TOKEN || '';
  if (token && !tokenPattern.test(token)) throw new Error('JARVIS_RUNTIME_TOKEN must contain 32–256 URL-safe characters');
  if (env.JARVIS_PILOT_REPOSITORY && !validRepository(env.JARVIS_PILOT_REPOSITORY)) {
    throw new Error('Invalid JARVIS_PILOT_REPOSITORY');
  }
  return { host, port, token, dryRun: env.JARVIS_DRY_RUN !== 'false', allowExternal: env.JARVIS_ALLOW_EXTERNAL === 'true' };
}

function authorize(req, config, env) {
  if (!config.token || !env.JARVIS_PILOT_REPOSITORY) throw new RuntimeError(503, 'runtime_not_configured');
  const authorizationHeaders = (req.rawHeaders || []).filter((value, index) => index % 2 === 0 && value.toLowerCase() === 'authorization');
  const header = req.headers.authorization;
  const match = typeof header === 'string' && /^Bearer ([A-Za-z0-9_-]{32,256})$/i.exec(header);
  if (authorizationHeaders.length > 1 || !match) throw new RuntimeError(401, 'unauthorized');
  const digest = value => createHash('sha256').update(value).digest();
  if (!timingSafeEqual(digest(config.token), digest(match[1]))) throw new RuntimeError(401, 'unauthorized');
}

async function readBody(req) {
  if (!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(req.headers['content-type'] || '')) {
    throw new RuntimeError(415, 'application_json_required');
  }
  if (req.headers['content-encoding'] && req.headers['content-encoding'] !== 'identity') {
    throw new RuntimeError(415, 'content_encoding_not_supported');
  }
  const length = req.headers['content-length'];
  if (length !== undefined && (!/^\d+$/.test(length) || Number(length) > MAX_BODY_BYTES)) {
    throw new RuntimeError(413, 'request_body_too_large');
  }
  const chunks = [];
  let size = 0;
  // Keep the stream alive long enough to send a 413 when a chunked body exceeds its limit.
  for await (const chunk of req.iterator({ destroyOnReturn: false })) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += bytes.length;
    if (size > MAX_BODY_BYTES) throw new RuntimeError(413, 'request_body_too_large');
    chunks.push(bytes);
  }
  try {
    return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks)));
  } catch {
    throw new RuntimeError(400, 'invalid_json');
  }
}

export function createRequestHandler(env = process.env, { invokeProviders = orchestrate } = {}) {
  const runtimeEnv = Object.freeze({ ...env });
  const config = runtimeConfig(runtimeEnv);
  let providerTaskInFlight = false;
  return async (req, res) => {
    res.setHeader('content-type', 'application/json');
    res.setHeader('cache-control', 'no-store');
    res.setHeader('x-content-type-options', 'nosniff');
    const send = (status, body) => {
      if (!res.destroyed && !res.writableEnded) {
        res.statusCode = status;
        res.end(JSON.stringify(body));
      }
    };
    if (req.method === 'GET' && req.url === '/health') {
      send(200, {
        ok: true, service: 'ai-jarvis-runtime', mode: 'local_pilot',
        dryRun: config.dryRun, configured: Boolean(config.token && runtimeEnv.JARVIS_PILOT_REPOSITORY),
        externalInvocationEnabled: !config.dryRun && config.allowExternal, execute: false
      });
      return;
    }
    if (req.method !== 'POST' || req.url !== '/tasks') {
      send(404, { error: 'not_found', execute: false });
      return;
    }
    let ownsProviderSlot = false;
    try {
      authorize(req, config, runtimeEnv);
      const input = await readBody(req);
      const plan = planTask(input, runtimeEnv);
      if (config.dryRun || plan.status === 'approval_required') {
        send(200, plan);
        return;
      }
      if (!config.allowExternal) throw new RuntimeError(403, 'external_invocation_disabled');
      if (providerTaskInFlight) throw new RuntimeError(429, 'provider_task_already_running');
      providerTaskInFlight = true;
      ownsProviderSlot = true;
      const result = await invokeProviders(input, runtimeEnv);
      send(200, { ...result, execute: false });
    } catch (error) {
      const known = error instanceof RuntimeError;
      const status = known ? error.status : 502;
      if (status === 401) res.setHeader('www-authenticate', 'Bearer realm="jarvis-runtime"');
      res.setHeader('connection', 'close');
      send(status, { error: known ? error.code : 'request_failed', execute: false });
      req.resume();
    } finally {
      if (ownsProviderSlot) providerTaskInFlight = false;
    }
  };
}

export function createRuntimeServer(env = process.env, dependencies = {}) {
  return http.createServer({
    maxHeaderSize: 8192, headersTimeout: 10_000, requestTimeout: 15_000,
    keepAliveTimeout: 5000, connectionsCheckingInterval: 1000
  }, createRequestHandler(env, dependencies));
}

export function startRuntime(env = process.env) {
  const config = runtimeConfig(env);
  const server = createRuntimeServer(env);
  server.listen(config.port, config.host, () => {
    console.log(`Jarvis local pilot listening on ${config.host}:${config.port}; dryRun=${config.dryRun}`);
  });
  return server;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) startRuntime();
