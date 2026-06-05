#!/usr/bin/env npx tsx
/**
 * Native-ollama reviewer runner (replaces the opencode path).
 *
 * Why native: opencode drives ollama over the OpenAI-compatible /v1 endpoint,
 * which has no `think` parameter, so gemma4's thinking stays on and swallows the
 * review output. ollama's native /api/chat supports `think:false` AND tools, so
 * we drive it directly.
 *
 * Conditions:
 *   control   — /api/chat, think:false, NO tools (reviews the inlined code).
 *   treatment — same + a single `query_context` tool; on a tool call we forward
 *               to the aictrl MCP (X-API-Key) and feed the result back.
 *
 * Usage:
 *   AICTRL_MCP_TOKEN=... npx tsx run-native.ts --condition control --rep 1 [--task 101]
 * Writes results/raw/rep-<rep>/<condition>/<class>s/PR-<id>.findings.json
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildPrompt } from './build-prompt.ts';
import { extractFindings } from './parse-findings.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP = path.resolve(HERE, '..');
const OLLAMA = process.env.OLLAMA_URL ?? 'http://localhost:11434';
const MODEL = process.env.CR_MODEL ?? 'gemma4:12b-cr';
const MCP_URL = 'https://aictrl.dev/aictrl/mcp';
const MAX_TOOL_TURNS = 6;

interface Task { id: number; class: 'file' | 'module'; title: string; paths: string[]; }
interface ChatMsg { role: string; content: string; tool_calls?: unknown[]; tool_name?: string; }

const QUERY_CONTEXT_TOOL = {
  type: 'function',
  function: {
    name: 'query_context',
    description:
      'Explore the project codebase. Use action "search" with a symbol/function name to find where it is defined, or action "callers" with a function name to find who calls it. Always pass domain "code".',
    parameters: {
      type: 'object',
      properties: {
        domain: { type: 'string', description: 'always "code"' },
        action: { type: 'string', description: '"search" or "callers"' },
        query: { type: 'string', description: 'the symbol or function name' },
      },
      required: ['domain', 'action', 'query'],
    },
  },
};

// ---- aictrl MCP (StreamableHTTP, X-API-Key) ----
function sseResult(text: string): any {
  const line = text.split('\n').find((l) => l.startsWith('data:') && l.includes('"id"'));
  return line ? JSON.parse(line.slice(5)) : null;
}
async function mcpHeaders(token: string, sid?: string): Promise<Record<string, string>> {
  const h: Record<string, string> = {
    'X-API-Key': token,
    'Content-Type': 'application/json',
    Accept: 'application/json, text/event-stream',
  };
  if (sid) h['Mcp-Session-Id'] = sid;
  return h;
}
async function mcpInit(token: string): Promise<string> {
  const r = await fetch(MCP_URL, {
    method: 'POST', headers: await mcpHeaders(token),
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'cr-local-kg', version: '1' } } }),
  });
  const sid = r.headers.get('mcp-session-id') ?? '';
  await fetch(MCP_URL, { method: 'POST', headers: await mcpHeaders(token, sid), body: JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) });
  return sid;
}
async function mcpQueryContext(token: string, sid: string, args: Record<string, unknown>): Promise<string> {
  const r = await fetch(MCP_URL, {
    method: 'POST', headers: await mcpHeaders(token, sid),
    body: JSON.stringify({ jsonrpc: '2.0', id: 9, method: 'tools/call', params: { name: 'query_context', arguments: args } }),
  });
  const j = sseResult(await r.text());
  return j?.result?.content?.[0]?.text ?? JSON.stringify(j?.result ?? j?.error ?? {});
}

// ---- ollama native chat (think:false) ----
async function chat(messages: ChatMsg[], tools: unknown[] | undefined, seed: number): Promise<ChatMsg> {
  const body: Record<string, unknown> = {
    model: MODEL, messages, think: false, stream: false,
    options: { temperature: 0.7, seed, num_predict: 4000 },
  };
  if (tools) body.tools = tools;
  const r = await fetch(`${OLLAMA}/api/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json();
  return (j.message ?? { role: 'assistant', content: '' }) as ChatMsg;
}

interface RunResult { content: string; toolCalls: number; }

async function reviewControl(userPrompt: string, seed: number): Promise<RunResult> {
  const m = await chat([{ role: 'user', content: userPrompt }], undefined, seed);
  return { content: m.content ?? '', toolCalls: 0 };
}

async function reviewTreatment(userPrompt: string, seed: number, token: string, sid: string): Promise<RunResult> {
  const messages: ChatMsg[] = [{ role: 'user', content: userPrompt }];
  let toolCalls = 0;
  for (let turn = 0; turn < MAX_TOOL_TURNS; turn += 1) {
    const m = await chat(messages, [QUERY_CONTEXT_TOOL], seed);
    messages.push({ role: 'assistant', content: m.content ?? '', tool_calls: m.tool_calls });
    const calls = (m.tool_calls ?? []) as Array<{ function: { name: string; arguments: unknown } }>;
    if (calls.length === 0) return { content: m.content ?? '', toolCalls };
    for (const tc of calls) {
      toolCalls += 1;
      let args = tc.function.arguments as Record<string, unknown>;
      if (typeof args === 'string') { try { args = JSON.parse(args); } catch { args = {}; } }
      if (!args.domain) args.domain = 'code';
      let result: string;
      try { result = await mcpQueryContext(token, sid, args); } catch (e) { result = `tool error: ${(e as Error).message}`; }
      messages.push({ role: 'tool', tool_name: 'query_context', content: String(result).slice(0, 4000) });
    }
  }
  // tool budget exhausted — force a final answer with no tools
  const m = await chat([...messages, { role: 'user', content: 'Now output ONLY your findings JSON array.' }], undefined, seed);
  return { content: m.content ?? '', toolCalls };
}

async function main(): Promise<void> {
  const a: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i += 1) if (argv[i].startsWith('--')) { a[argv[i].slice(2)] = argv[i + 1] ?? ''; i += 1; }
  const condition = a.condition as 'control' | 'treatment';
  const rep = Number(a.rep);
  if (!['control', 'treatment'].includes(condition) || !Number.isFinite(rep)) {
    console.error('usage: run-native.ts --condition control|treatment --rep N [--task ID]');
    process.exit(1);
  }
  const cfg = JSON.parse(fs.readFileSync(path.join(EXP, 'tasks/tasks.json'), 'utf8')) as { pinDir: string; tasks: Task[] };
  const reviewMd = fs.readFileSync(path.join(EXP, 'prompts/review.md'), 'utf8');
  const tasks = a.task ? cfg.tasks.filter((t) => String(t.id) === a.task) : cfg.tasks;

  let token = '', sid = '';
  if (condition === 'treatment') {
    token = process.env.AICTRL_MCP_TOKEN ?? '';
    if (!token) { console.error('treatment needs AICTRL_MCP_TOKEN'); process.exit(1); }
    sid = await mcpInit(token);
    console.error(`mcp session: ${sid.slice(0, 10)}…`);
  }

  for (const task of tasks) {
    const userPrompt = buildPrompt(reviewMd, cfg.pinDir, task.paths);
    const t0 = Date.now();
    const res = condition === 'control'
      ? await reviewControl(userPrompt, rep)
      : await reviewTreatment(userPrompt, rep, token, sid);
    const findings = extractFindings(res.content);
    const outDir = path.join(EXP, 'results/raw', `rep-${rep}`, condition, `${task.class}s`);
    fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(path.join(outDir, `PR-${task.id}.findings.json`), JSON.stringify({ prNumber: task.id, findings }, null, 2));
    console.error(`[${condition} rep${rep}] task ${task.id} (${task.class}): ${findings.length} findings, ${res.toolCalls} tool calls, ${(Date.now() - t0) / 1000 | 0}s`);
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
