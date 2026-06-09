#!/usr/bin/env npx tsx
/**
 * cr-local-kg results pipeline.
 *
 * Aggregates the sweep's raw per-review artefacts into a single, deterministic
 * summary (structured JSON + a printed markdown report). Reuses cr-loop's
 * score(), configured for strict precision: file+line±5 matching, no severity
 * gate, and unmatched findings counted as false positives while still reported
 * separately as novels.
 *
 * For each condition (control, treatment), OVERALL and per task-class
 * (file, module), across the requested reps, it computes:
 *   - micro-averaged precision / recall / F1 / F2 (sum TP/FP/FN over reviews
 *     first), plus raw TP/FP/FN/novels totals and the review count n.
 *   - KG usage: # reviews with >=1 query_context call, % of reviews, avg
 *     calls/review, and a histogram by KG action (callers/impact/search/...)
 *     parsed from the session.json tool-call args.
 *   - tokens: total + avg OUTPUT tokens/review (output is additive/accurate),
 *     total reasoning tokens, avg model-steps/review, plus a CUMULATIVE input
 *     figure (explicitly labelled — it re-counts re-sent context, so it is NOT
 *     unique token usage).
 *   - time/review: avg and median seconds.
 * It also computes treatment-vs-control ΔF1 overall and per class.
 *
 * Robustness: a missing dir / unparseable file never crashes the run — it is
 * skipped and counted, and coverage (reviews actually scored vs 20 expected)
 * is reported per cell.
 *
 * Data formats (verified against results/raw):
 *   raw/rep-<R>/<condition>/<files|modules>/PR-<id>.findings.json
 *     { prNumber, findings: [ { file, line, severity, title, description } ] }
 *   raw/.../PR-<id>.session.json  — JSONL (one JSON event per line). Token
 *     usage lives on `step_finish` events at part.tokens (one per model step,
 *     distinct cumulative values). KG calls are `tool_use` events whose
 *     part.tool === "aictrl_query_context" with part.state.input.action.
 *   raw/.../PR-<id>.meta.json     — { prNumber, condition, rep, class,
 *     durationSeconds, queryContextCalls, findings }
 *   results/timing.csv            — task,class,condition,rep,findings,kg_calls,seconds
 *
 * Usage: pipeline.ts [--reps 1,2,3] [--out results/summary.json]
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { score, type SkillFinding } from '../../cr-loop/scripts/score.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP = path.resolve(HERE, '..');
const DEFAULT_ANSWER_KEY = path.join(EXP, 'answer-key.json');
const DEFAULT_BASE = path.join(EXP, 'results', 'raw');
const SCORE_OPTIONS = {
  countNovelFindingsAsFalsePositives: true,
  requireSeverityMatch: false,
} as const;

export const CONDITIONS = ['control', 'treatment'] as const;
export type Condition = (typeof CONDITIONS)[number];
/** class label -> directory name */
export const CLASSES: Array<{ label: 'file' | 'module'; dir: 'files' | 'modules' }> = [
  { label: 'file', dir: 'files' },
  { label: 'module', dir: 'modules' },
];
/** 15 file tasks + 5 module tasks. */
const EXPECTED_PER_CELL: Record<'file' | 'module', number> = { file: 15, module: 5 };

/** Known KG actions; the histogram also records any unexpected action verbatim. */
export const KG_ACTIONS = [
  'callers',
  'impact',
  'search',
  'co_changes',
  'context',
  'deps',
  'read',
  'traverse',
  'skeleton',
] as const;

const r3 = (n: number): number => Math.round(n * 1000) / 1000;

// ---------------------------------------------------------------------------
// Accumulators
// ---------------------------------------------------------------------------
interface Cell {
  n: number; // reviews actually scored
  expected: number;
  skipped: number; // findings files present but unparseable
  // scoring
  tp: number;
  fp: number;
  fn: number;
  novels: number;
  // kg
  kgReviews: number; // reviews with >=1 query_context call
  kgCalls: number; // total query_context calls
  kgActions: Record<string, number>;
  // tokens
  outputTokens: number;
  reasoningTokens: number;
  inputTokensCumulative: number;
  modelSteps: number;
  sessionsParsed: number;
  // time
  seconds: number[];
}

function blankCell(expected: number): Cell {
  return {
    n: 0,
    expected,
    skipped: 0,
    tp: 0,
    fp: 0,
    fn: 0,
    novels: 0,
    kgReviews: 0,
    kgCalls: 0,
    kgActions: {},
    outputTokens: 0,
    reasoningTokens: 0,
    inputTokensCumulative: 0,
    modelSteps: 0,
    sessionsParsed: 0,
    seconds: [],
  };
}

// ---------------------------------------------------------------------------
// Session parsing (token usage + KG action histogram), fail-soft.
// ---------------------------------------------------------------------------
export interface SessionStats {
  outputTokens: number;
  reasoningTokens: number;
  inputTokensCumulative: number;
  modelSteps: number;
  kgCalls: number;
  kgActions: Record<string, number>;
}

interface TokenObj {
  total?: number;
  input?: number;
  output?: number;
  reasoning?: number;
}

/**
 * Parse a session JSONL dump. Tokens are taken from `step_finish` events
 * (one per model step, distinct cumulative values) — NOT from the duplicated
 * `message_complete` events, which would double/triple-count. KG calls come
 * from `tool_use` events for the aictrl_query_context tool.
 */
export function parseSession(raw: string): SessionStats {
  const out: SessionStats = {
    outputTokens: 0,
    reasoningTokens: 0,
    inputTokensCumulative: 0,
    modelSteps: 0,
    kgCalls: 0,
    kgActions: {},
  };
  for (const line of raw.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    let ev: Record<string, unknown>;
    try {
      ev = JSON.parse(t) as Record<string, unknown>;
    } catch {
      continue; // skip malformed line, keep going
    }
    const type = ev.type;
    const part = (ev.part ?? {}) as Record<string, unknown>;

    if (type === 'step_finish') {
      const tok = part.tokens as TokenObj | undefined;
      if (tok) {
        out.modelSteps += 1;
        out.outputTokens += Number(tok.output ?? 0);
        out.reasoningTokens += Number(tok.reasoning ?? 0);
        out.inputTokensCumulative += Number(tok.input ?? 0);
      }
    } else if (type === 'tool_use') {
      const tool = part.tool;
      if (tool === 'aictrl_query_context') {
        out.kgCalls += 1;
        const state = (part.state ?? {}) as Record<string, unknown>;
        const input = (state.input ?? {}) as Record<string, unknown>;
        const action = typeof input.action === 'string' ? input.action : 'unknown';
        out.kgActions[action] = (out.kgActions[action] ?? 0) + 1;
      }
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// Aggregation
// ---------------------------------------------------------------------------
function prf(tp: number, fp: number, fn: number): { precision: number; recall: number; f1: number; f2: number } {
  const precision = tp + fp === 0 ? 0 : tp / (tp + fp);
  const recall = tp + fn === 0 ? 0 : tp / (tp + fn);
  const f1 = precision + recall === 0 ? 0 : (2 * precision * recall) / (precision + recall);
  const f2 = 4 * precision + recall === 0 ? 0 : (5 * precision * recall) / (4 * precision + recall);
  return { precision, recall, f1, f2 };
}

function median(xs: number[]): number {
  if (xs.length === 0) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

/** Read a JSON file fail-soft. Returns undefined on any error. */
function readJson<T>(file: string): T | undefined {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8')) as T;
  } catch {
    return undefined;
  }
}

interface ScoredCell {
  n: number;
  expected: number;
  coverage: number; // n / expected
  skipped: number;
  truePositives: number;
  falsePositives: number;
  falseNegatives: number;
  novelFindings: number;
  precision: number;
  recall: number;
  f1: number;
  f2: number;
  kg: {
    reviewsWithCalls: number;
    pctReviewsWithCalls: number;
    avgCallsPerReview: number;
    totalCalls: number;
    byAction: Record<string, number>;
  };
  tokens: {
    totalOutput: number;
    avgOutputPerReview: number;
    totalReasoning: number;
    avgModelStepsPerReview: number;
    'input (cumulative across steps, re-counts re-sent context)': number;
    sessionsParsed: number;
  };
  time: {
    avgSeconds: number;
    medianSeconds: number;
    nTimed: number;
  };
}

/** Stable key ordering for the action histogram: known actions first, then extras alphabetically. */
function orderActions(h: Record<string, number>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const a of KG_ACTIONS) if (h[a] !== undefined) out[a] = h[a];
  for (const k of Object.keys(h).sort()) if (!(k in out)) out[k] = h[k];
  return out;
}

function finalizeCell(c: Cell): ScoredCell {
  const { precision, recall, f1, f2 } = prf(c.tp, c.fp, c.fn);
  return {
    n: c.n,
    expected: c.expected,
    coverage: c.expected === 0 ? 0 : r3(c.n / c.expected),
    skipped: c.skipped,
    truePositives: r3(c.tp),
    falsePositives: r3(c.fp),
    falseNegatives: r3(c.fn),
    novelFindings: c.novels,
    precision: r3(precision),
    recall: r3(recall),
    f1: r3(f1),
    f2: r3(f2),
    kg: {
      reviewsWithCalls: c.kgReviews,
      pctReviewsWithCalls: c.n === 0 ? 0 : r3((100 * c.kgReviews) / c.n),
      avgCallsPerReview: c.n === 0 ? 0 : r3(c.kgCalls / c.n),
      totalCalls: c.kgCalls,
      byAction: orderActions(c.kgActions),
    },
    tokens: {
      totalOutput: c.outputTokens,
      avgOutputPerReview: c.n === 0 ? 0 : r3(c.outputTokens / c.n),
      totalReasoning: c.reasoningTokens,
      avgModelStepsPerReview: c.sessionsParsed === 0 ? 0 : r3(c.modelSteps / c.sessionsParsed),
      'input (cumulative across steps, re-counts re-sent context)': c.inputTokensCumulative,
      sessionsParsed: c.sessionsParsed,
    },
    time: {
      avgSeconds: c.seconds.length === 0 ? 0 : r3(c.seconds.reduce((a, b) => a + b, 0) / c.seconds.length),
      medianSeconds: r3(median(c.seconds)),
      nTimed: c.seconds.length,
    },
  };
}

export interface AggregateOptions {
  reps: number[];
  answerKeyPath?: string;
  baseDir?: string;
}

export interface ConditionSummary {
  overall: ScoredCell;
  byClass: { file: ScoredCell; module: ScoredCell };
}

export interface Summary {
  generatedAt: string;
  reps: number[];
  answerKeyPath: string;
  baseDir: string;
  conditions: { control: ConditionSummary; treatment: ConditionSummary };
  deltas: {
    // null when the bucket is not comparable (control or treatment coverage < 100%).
    // A partial sweep scored against full expectations reads missing reviews as F1=0,
    // so a delta over unequal coverage is a data-completeness artifact, not a result.
    f1Overall: number | null;
    f1File: number | null;
    f1Module: number | null;
    f2Overall: number | null;
    f2File: number | null;
    f2Module: number | null;
  };
  deltasNote?: string;
}

export function aggregate(opts: AggregateOptions): Summary {
  const reps = [...opts.reps].sort((a, b) => a - b);
  const answerKeyPath = opts.answerKeyPath ?? DEFAULT_ANSWER_KEY;
  const baseDir = opts.baseDir ?? DEFAULT_BASE;

  const result = {} as { control: ConditionSummary; treatment: ConditionSummary };

  for (const cond of CONDITIONS) {
    const overall = blankCell(reps.length * (EXPECTED_PER_CELL.file + EXPECTED_PER_CELL.module));
    const byClass: Record<'file' | 'module', Cell> = {
      file: blankCell(reps.length * EXPECTED_PER_CELL.file),
      module: blankCell(reps.length * EXPECTED_PER_CELL.module),
    };

    for (const rep of reps) {
      for (const { label, dir: sub } of CLASSES) {
        const dir = path.join(baseDir, `rep-${rep}`, cond, sub);
        let entries: string[];
        try {
          entries = fs.readdirSync(dir);
        } catch {
          continue; // missing dir — partial sweep, skip fail-soft
        }
        const findingFiles = entries.filter((f) => /^PR-\d+\.findings\.json$/.test(f)).sort();
        for (const f of findingFiles) {
          const pr = Number(f.match(/^PR-(\d+)\./)?.[1]);
          const data = readJson<{ prNumber?: number; findings?: SkillFinding[] }>(path.join(dir, f));
          if (!data || !Array.isArray(data.findings)) {
            overall.skipped += 1;
            byClass[label].skipped += 1;
            continue;
          }
          const prNumber = data.prNumber ?? pr;
          let res;
          try {
            res = score(prNumber, data.findings, answerKeyPath, SCORE_OPTIONS);
          } catch {
            overall.skipped += 1;
            byClass[label].skipped += 1;
            continue;
          }
          for (const c of [overall, byClass[label]]) {
            c.n += 1;
            c.tp += res.totals.truePositives;
            c.fp += res.totals.falsePositives;
            c.fn += res.totals.falseNegatives;
            c.novels += res.totals.novelFindings;
          }

          // Session-derived token + KG stats (fail-soft).
          const stem = f.replace(/\.findings\.json$/, '');
          const sessionPath = path.join(dir, `${stem}.session.json`);
          if (fs.existsSync(sessionPath)) {
            let sraw: string | undefined;
            try {
              sraw = fs.readFileSync(sessionPath, 'utf8');
            } catch {
              sraw = undefined;
            }
            if (sraw !== undefined) {
              const s = parseSession(sraw);
              for (const c of [overall, byClass[label]]) {
                c.sessionsParsed += 1;
                c.outputTokens += s.outputTokens;
                c.reasoningTokens += s.reasoningTokens;
                c.inputTokensCumulative += s.inputTokensCumulative;
                c.modelSteps += s.modelSteps;
                c.kgCalls += s.kgCalls;
                if (s.kgCalls > 0) c.kgReviews += 1;
                for (const [act, cnt] of Object.entries(s.kgActions)) {
                  c.kgActions[act] = (c.kgActions[act] ?? 0) + cnt;
                }
              }
            }
          }

          // Time: prefer meta.json durationSeconds (fail-soft).
          const meta = readJson<{ durationSeconds?: number }>(path.join(dir, `${stem}.meta.json`));
          if (meta && typeof meta.durationSeconds === 'number') {
            overall.seconds.push(meta.durationSeconds);
            byClass[label].seconds.push(meta.durationSeconds);
          }
        }
      }
    }

    result[cond] = {
      overall: finalizeCell(overall),
      byClass: { file: finalizeCell(byClass.file), module: finalizeCell(byClass.module) },
    };
  }

  // Only emit a ΔF1 when BOTH conditions fully cover the bucket. Otherwise a partial
  // treatment sweep (e.g. module n=0 scored as F1=0) would publish a phantom negative.
  const cmpDelta = (t: ScoredCell, c: ScoredCell): number | null =>
    t.coverage === 1 && c.coverage === 1 ? r3(t.f1 - c.f1) : null;
  const deltas = {
    f1Overall: cmpDelta(result.treatment.overall, result.control.overall),
    f1File: cmpDelta(result.treatment.byClass.file, result.control.byClass.file),
    f1Module: cmpDelta(result.treatment.byClass.module, result.control.byClass.module),
    f2Overall:
      result.treatment.overall.coverage === 1 && result.control.overall.coverage === 1
        ? r3(result.treatment.overall.f2 - result.control.overall.f2)
        : null,
    f2File:
      result.treatment.byClass.file.coverage === 1 && result.control.byClass.file.coverage === 1
        ? r3(result.treatment.byClass.file.f2 - result.control.byClass.file.f2)
        : null,
    f2Module:
      result.treatment.byClass.module.coverage === 1 && result.control.byClass.module.coverage === 1
        ? r3(result.treatment.byClass.module.f2 - result.control.byClass.module.f2)
        : null,
  };
  const suppressed = Object.values(deltas).some((v) => v === null);

  return {
    generatedAt: new Date().toISOString(),
    reps,
    answerKeyPath,
    baseDir,
    conditions: result,
    deltas,
    ...(suppressed
      ? {
          deltasNote:
            'Some delta values are null: control and treatment coverage differ for those buckets, so the comparison is not apples-to-apples (a partial sweep is scored against full expectations, reading missing reviews as F1/F2=0). Complete the treatment sweep to obtain comparable deltas.',
        }
      : {}),
  };
}

// ---------------------------------------------------------------------------
// Markdown report
// ---------------------------------------------------------------------------
function cellRow(label: string, c: ScoredCell): string {
  const actions = Object.entries(c.kg.byAction)
    .map(([a, n]) => `${a}:${n}`)
    .join(' ') || '-';
  return [
    label,
    `${c.n}/${c.expected}`,
    c.precision.toFixed(3),
    c.recall.toFixed(3),
    c.f1.toFixed(3),
    c.f2.toFixed(3),
    `${c.truePositives}/${c.falsePositives}/${c.falseNegatives}`,
    c.novelFindings,
    `${c.kg.reviewsWithCalls} (${c.kg.pctReviewsWithCalls}%)`,
    c.kg.avgCallsPerReview.toFixed(3),
    c.tokens.avgOutputPerReview.toFixed(3),
    c.tokens.avgModelStepsPerReview.toFixed(3),
    c.time.avgSeconds.toFixed(3),
    c.time.medianSeconds.toFixed(3),
    actions,
  ].join(' | ');
}

export function renderReport(s: Summary): string {
  const L: string[] = [];
  L.push(`# cr-local-kg results summary`);
  L.push('');
  L.push(`- reps: ${s.reps.join(', ') || '(none)'}`);
  L.push(`- answer-key: ${s.answerKeyPath}`);
  L.push(`- generated: ${s.generatedAt}`);
  L.push(`- scoring: file+line±5, severity ignored, novel/unmatched findings counted as FP`);
  L.push('');
  L.push(`> Token "input (cumulative)" is omitted from the table because it re-counts re-sent`);
  L.push(`> context across steps and is not unique usage; see summary.json for the raw figure.`);
  L.push('');

  const header =
    'scope | n/exp | P | R | F1 | F2 | TP/FP/FN | novels | KG reviews | KG/rev | out tok/rev | steps/rev | avg s | med s | KG actions';
  const divider = header
    .split('|')
    .map(() => '---')
    .join(' | ');

  for (const cond of CONDITIONS) {
    const cs = s.conditions[cond];
    L.push(`## ${cond.toUpperCase()}`);
    L.push('');
    L.push(header);
    L.push(divider);
    L.push(cellRow('overall', cs.overall));
    L.push(cellRow('file', cs.byClass.file));
    L.push(cellRow('module', cs.byClass.module));
    L.push('');
    const skipped = cs.overall.skipped;
    if (skipped > 0) L.push(`_skipped (unparseable) findings files: ${skipped}_`);
    L.push('');
  }

  L.push(`## Treatment − Control`);
  L.push('');
  L.push('scope | ΔF1 | ΔF2');
  L.push('--- | --- | ---');
  const fmtD = (v: number | null): string =>
    v === null ? 'n/a (coverage <100%)' : `${v >= 0 ? '+' : ''}${v.toFixed(3)}`;
  L.push(`overall | ${fmtD(s.deltas.f1Overall)} | ${fmtD(s.deltas.f2Overall)}`);
  L.push(`file | ${fmtD(s.deltas.f1File)} | ${fmtD(s.deltas.f2File)}`);
  L.push(`module | ${fmtD(s.deltas.f1Module)} | ${fmtD(s.deltas.f2Module)}`);
  L.push('');
  if (s.deltasNote) {
    L.push(`> ${s.deltasNote}`);
    L.push('');
  }

  return L.join('\n');
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------
function parseArgs(argv: string[]): { reps: number[]; out?: string; baseDir?: string } {
  const a: Record<string, string> = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) {
      a[argv[i].slice(2)] = argv[i + 1] ?? '';
      i += 1;
    }
  }
  const reps = (a.reps ?? '1,2,3')
    .split(',')
    .map((x) => Number(x.trim()))
    .filter((x) => Number.isFinite(x));
  return { reps, out: a.out, baseDir: a['base-dir'] };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const { reps, out, baseDir } = parseArgs(process.argv.slice(2));
  const summary = aggregate({ reps, ...(baseDir ? { baseDir: path.resolve(EXP, baseDir) } : {}) });
  const outPath = out ? path.resolve(EXP, out) : path.join(EXP, 'results', 'summary.json');
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, `${JSON.stringify(summary, null, 2)}\n`);
  console.log(renderReport(summary));
  console.error(`\nwrote ${outPath}`);
}
