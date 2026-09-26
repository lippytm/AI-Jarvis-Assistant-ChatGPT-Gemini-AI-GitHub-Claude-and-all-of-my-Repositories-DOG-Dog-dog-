import http from 'node:http';
import { orchestrate } from './orchestrator.mjs';

const port = Number(process.env.JARVIS_PORT || 8787);
const dryRun = process.env.JARVIS_DRY_RUN !== 'false';

const server = http.createServer(async (req, res) => {
  res.setHeader('content-type', 'application/json');
  if (req.method === 'GET' && req.url === '/health') {
    res.end(JSON.stringify({ ok: true, dryRun, service: 'ai-jarvis-runtime' }));
    return;
  }
  if (req.method !== 'POST' || req.url !== '/tasks') {
    res.statusCode = 404;
    res.end(JSON.stringify({ error: 'not_found' }));
    return;
  }
  try {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const result = await orchestrate(JSON.parse(Buffer.concat(chunks).toString('utf8')));
    res.statusCode = 200;
    res.end(JSON.stringify(result));
  } catch (error) {
    res.statusCode = 400;
    res.end(JSON.stringify({ error: error.message, execute: false }));
  }
});

server.listen(port, () => console.log(`Jarvis runtime listening on ${port}; dryRun=${dryRun}`));
