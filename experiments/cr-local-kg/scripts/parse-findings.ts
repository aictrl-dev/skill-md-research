// Tolerantly extract a findings array from a model's free-text answer.
import * as fs from 'node:fs';

export interface SkillFinding {
  file: string;
  line?: number | string;
  severity: string;
  title?: string;
  description?: string;
}

/** Every top-level JSON array substring in `text`, last first. */
function candidateArrays(text: string): string[] {
  const out: string[] = [];
  for (let i = 0; i < text.length; i += 1) {
    if (text[i] !== '[') continue;
    let depth = 0;
    for (let j = i; j < text.length; j += 1) {
      if (text[j] === '[') depth += 1;
      else if (text[j] === ']') {
        depth -= 1;
        if (depth === 0) { out.push(text.slice(i, j + 1)); break; }
      }
    }
  }
  return out.reverse();
}

function isFinding(x: unknown): x is SkillFinding {
  return !!x && typeof x === 'object'
    && typeof (x as Record<string, unknown>).file === 'string'
    && typeof (x as Record<string, unknown>).severity === 'string';
}

export function extractFindings(text: string): SkillFinding[] {
  for (const chunk of candidateArrays(text)) {
    try {
      const parsed = JSON.parse(chunk);
      if (Array.isArray(parsed)) {
        const findings = parsed.filter(isFinding);
        if (parsed.length === 0 || findings.length > 0) return findings;
      }
    } catch { /* keep scanning */ }
  }
  return [];
}

// CLI: parse-findings.ts --session <text-or-json file> --pr <id> --out <findings.json>
if (import.meta.url === `file://${process.argv[1]}`) {
  const a: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) { a[argv[i].slice(2)] = argv[i + 1] ?? ''; i += 1; }
  }
  const raw = fs.readFileSync(a.session, 'utf8');
  const findings = extractFindings(raw);
  fs.writeFileSync(a.out, JSON.stringify({ prNumber: Number(a.pr), findings }, null, 2));
  console.error(`parse-findings: ${findings.length} findings → ${a.out}`);
}
