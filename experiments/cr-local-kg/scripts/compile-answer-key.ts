// Compile gold/triaged/<id>.json files into one frozen answer key keyed by task id.
import * as fs from 'node:fs';
import * as path from 'node:path';

const VERDICTS = ['TRUE', 'FALSE', 'UNCERTAIN'];
const ACTIONS = ['FIX', 'DEFER', 'IGNORE'];

export interface AnswerKeyEntry {
  bot: string; severity: string; file: string; line: string; description: string;
  verdict: string; action: string; reason: string;
}

/** Read every gold/triaged/<id>.json and produce { "<id>": AnswerKeyEntry[] }. */
export function compileAnswerKey(triagedDir: string): Record<string, AnswerKeyEntry[]> {
  const out: Record<string, AnswerKeyEntry[]> = {};
  for (const f of fs.readdirSync(triagedDir).filter((x) => /^\d+\.json$/.test(x)).sort()) {
    const id = f.replace(/\.json$/, '');
    const arr = JSON.parse(fs.readFileSync(path.join(triagedDir, f), 'utf8')) as AnswerKeyEntry[];
    if (!Array.isArray(arr)) throw new Error(`compile: ${f} is not an array`);
    arr.forEach((e, i) => {
      if (!VERDICTS.includes(e.verdict)) throw new Error(`compile: task ${id} entry ${i} bad/missing verdict`);
      if (!ACTIONS.includes(e.action)) throw new Error(`compile: task ${id} entry ${i} bad/missing action`);
      e.line = String(e.line ?? '');
    });
    out[id] = arr;
  }
  return out;
}

// CLI: compile-answer-key.ts --triaged gold/triaged --out answer-key.json
if (import.meta.url === `file://${process.argv[1]}`) {
  const a: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) { a[argv[i].slice(2)] = argv[i + 1] ?? ''; i += 1; }
  }
  const key = compileAnswerKey(a.triaged ?? 'gold/triaged');
  fs.writeFileSync(a.out ?? 'answer-key.json', JSON.stringify(key, null, 2));
  const n = Object.values(key).reduce((s, v) => s + v.length, 0);
  console.error(`compile: ${Object.keys(key).length} tasks, ${n} labels → ${a.out ?? 'answer-key.json'}`);
}
