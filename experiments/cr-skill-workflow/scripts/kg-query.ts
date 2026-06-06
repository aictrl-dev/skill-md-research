#!/usr/bin/env npx tsx
/**
 * Deterministic KG client — calls the aictrl query_context MCP tool directly
 * (no model in the loop), so a script node can prefetch graph context.
 *
 * CLI: kg-query.ts --action callers --query <fn>           (single call, prints JSON)
 * Env: AICTRL_MCP_TOKEN must be set.
 * Also exported as queryContext() for the prefetch script.
 */
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';

const MCP_URL = 'https://aictrl.dev/aictrl/mcp';

let _client: Client | null = null;
async function getClient(): Promise<Client> {
  if (_client) return _client;
  const token = process.env.AICTRL_MCP_TOKEN;
  if (!token) throw new Error('AICTRL_MCP_TOKEN not set');
  const transport = new StreamableHTTPClientTransport(new URL(MCP_URL), {
    requestInit: { headers: { 'X-API-Key': token } },
  });
  const client = new Client({ name: 'kg-prefetch', version: '1.0.0' }, { capabilities: {} });
  await client.connect(transport);
  _client = client;
  return client;
}

export async function queryContext(domain: string, action: string, query: string, params?: object): Promise<unknown> {
  const client = await getClient();
  const res: any = await client.callTool({
    name: 'query_context',
    arguments: { domain, action, query, ...(params ? { params } : {}) },
  });
  // tool returns content blocks; pull text and try to JSON-parse
  const text = (res?.content ?? []).filter((c: any) => c.type === 'text').map((c: any) => c.text).join('\n');
  try { return JSON.parse(text); } catch { return text; }
}

export async function closeClient() { if (_client) { await _client.close(); _client = null; } }

// CLI
if (process.argv[1]?.endsWith('kg-query.ts')) {
  const a: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) if (argv[i].startsWith('--')) { a[argv[i].slice(2)] = argv[i + 1] ?? ''; i++; }
  (async () => {
    const out = await queryContext(a.domain ?? 'code', a.action ?? 'callers', a.query ?? '');
    process.stdout.write(JSON.stringify(out, null, 2) + '\n');
    await closeClient();
  })().catch(e => { console.error('kg-query error:', e.message); process.exit(1); });
}
