#!/usr/bin/env npx tsx
/**
 * Aggregate per-PR cr-loop scores for one variant into a single Experiments row,
 * plus a per-defect-class breakdown (one ClassBreakdown row per class that the
 * answer key labels via `category`).
 *
 * Reuses cr-loop's trusted score() per PR, then micro-averages: sum TP/FP/FN
 * across PRs and compute precision/recall/F1 from the sums (NOT a mean of
 * per-PR F1s, which would over-weight small PRs).
 *
 * SNR (TP/FP) and Significance (|ΔF1| vs the small-sample noise floor) are
 * DERIVED here; SNR is null when FP === 0, Significance is '' until a baseline
 * is supplied. With a single seed the best a positive ΔF1 earns is
 * 'inconclusive' — 'confirmed' is reserved for multi-seed runs (set manually).
 *
 * Usage:
 *   npx tsx aggregate.ts --findings-dir <dir> --answer-key <orig|extended> \
 *     --experiment csharp-review --hypothesis H-001 --variant "Phase E" \
 *     --skill-version code-review.SKILL.v3.md --model zai-coding-plan/glm-5.1 \
 *     --tool-config "KG:populated" [--baseline-f1 0.369] [--cost "$1.20"] \
 *     [--latency "1200/3400"] [--tokens-per-pr 9000] \
 *     [--annotation-coverage dense] [--seed 1] [--log-link log/004.md] \
 *     [--out row.json] [--breakdown-out breakdown.json]
 *
 * Back-compat: --kg-state <empty|populated> maps to --tool-config "KG:<value>".
 * For tests, pass --answer-key-path + --answer-key-version.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { score, type SkillFinding, type CategoryTotals } from '../../cr-loop/scripts/score.ts';
import {
  type ExperimentRow,
  type ClassBreakdownRow,
  type AnswerKeyVersion,
  type DefectClass,
  ANSWER_KEY_VERSIONS,
  DEFECT_CLASSES,
  validateExperimentRow,
  validateClassBreakdownRow,
} from './schema.ts';

const round3 = (n: number): number => Math.round(n * 1000) / 1000;

/** ΔF1 within this band of zero is indistinguishable from single-seed noise. */
export const NOISE_FLOOR = 0.01;

const prf = (tp: number, fp: number, fn: number): { precision: number; recall: number; f1: number } => {
  const precision = tp + fp === 0 ? 0 : tp / (tp + fp);
  const recall = tp + fn === 0 ? 0 : tp / (tp + fn);
  const f1 = precision + recall === 0 ? 0 : (2 * precision * recall) / (precision + recall);
  return { precision, recall, f1 };
};

export interface AggregateMeta {
  experiment: string;
  hId: string;
  variant: string;
  skillVersion: string;
  model: string;
  toolContextConfig: string;
  baselineF1?: number | null;
  cost?: string;
  logLink?: string;
  latency?: string;
  tokensPerPr?: number | null;
  annotationCoverage?: ExperimentRow['annotationCoverage'];
  seed?: string;
}

export interface AggregateResult {
  row: ExperimentRow;
  breakdown: ClassBreakdownRow[];
}

export function aggregate(
  findingsDir: string,
  answerKeyPath: string,
  answerKeyVersion: AnswerKeyVersion,
  meta: AggregateMeta,
): AggregateResult {
  if (!fs.existsSync(findingsDir) || !fs.statSync(findingsDir).isDirectory()) {
    throw new Error(`aggregate: findings dir not found: ${findingsDir}`);
  }
  const files = fs
    .readdirSync(findingsDir)
    .filter((f) => /^PR-\d+\.findings\.json$/.test(f))
    .sort();
  if (files.length === 0) {
    throw new Error(`aggregate: no PR-*.findings.json files in ${findingsDir}`);
  }

  let tp = 0, fp = 0, fn = 0, novels = 0;
  const byCategory: Record<string, CategoryTotals> = {};
  const acc = (cat: string): CategoryTotals => (byCategory[cat] ??= { tp: 0, fp: 0, fn: 0, novels: 0 });

  for (const file of files) {
    const full = path.join(findingsDir, file);
    const data = JSON.parse(fs.readFileSync(full, 'utf8')) as {
      prNumber?: number;
      findings?: SkillFinding[];
    };
    if (!Array.isArray(data.findings)) {
      throw new Error(`aggregate: '${file}' has no 'findings' array`);
    }
    const prNumber = data.prNumber ?? Number(file.match(/^PR-(\d+)\./)?.[1]);
    if (!Number.isFinite(prNumber)) {
      throw new Error(`aggregate: cannot determine PR number for '${file}'`);
    }
    const r = score(prNumber, data.findings, answerKeyPath);
    tp += r.totals.truePositives;
    fp += r.totals.falsePositives;
    fn += r.totals.falseNegatives;
    novels += r.totals.novelFindings;
    for (const [cat, t] of Object.entries(r.totals.byCategory)) {
      const b = acc(cat);
      b.tp += t.tp; b.fp += t.fp; b.fn += t.fn; b.novels += t.novels;
    }
  }

  const { precision, recall, f1 } = prf(tp, fp, fn);
  const baseline = meta.baselineF1 ?? null;
  const deltaF1 = baseline === null ? null : round3(f1 - baseline);
  const snr = fp === 0 ? null : round3(tp / fp);

  let significance: ExperimentRow['significance'] = '';
  if (deltaF1 !== null) significance = Math.abs(deltaF1) < NOISE_FLOOR ? 'noise' : 'inconclusive';

  const row: ExperimentRow = {
    experiment: meta.experiment,
    hId: meta.hId,
    variant: meta.variant,
    skillVersion: meta.skillVersion,
    model: meta.model,
    toolContextConfig: meta.toolContextConfig,
    answerKeyVersion,
    nPrs: files.length,
    tp: round3(tp),
    fp: round3(fp),
    fn: round3(fn),
    novels,
    precision: round3(precision),
    recall: round3(recall),
    f1: round3(f1),
    deltaF1,
    cost: meta.cost ?? '',
    logLink: meta.logLink ?? '',
    snr,
    latency: meta.latency ?? '',
    tokensPerPr: meta.tokensPerPr ?? null,
    annotationCoverage: meta.annotationCoverage ?? '',
    seed: meta.seed ?? '',
    significance,
  };

  // One breakdown row per *categorised* class (skip the '' uncategorised bucket,
  // e.g. cr-loop, whose answer key predates the taxonomy). Unknown labels → 'other'.
  const breakdown: ClassBreakdownRow[] = Object.entries(byCategory)
    .filter(([cat, t]) => cat !== '' && t.tp + t.fp + t.fn > 0)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([cat, t]) => {
      const known = (DEFECT_CLASSES as readonly string[]).includes(cat);
      const m = prf(t.tp, t.fp, t.fn);
      return {
        experiment: meta.experiment,
        hId: meta.hId,
        answerKeyVersion,
        defectClass: (known ? cat : 'other') as DefectClass,
        tp: round3(t.tp),
        fp: round3(t.fp),
        fn: round3(t.fn),
        precision: round3(m.precision),
        recall: round3(m.recall),
        f1: round3(m.f1),
        notes: known ? '' : `label '${cat}' not in taxonomy → mapped to 'other'`,
      };
    });

  return { row, breakdown };
}

// ---- CLI ----
function argMap(argv: string[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i].startsWith('--')) {
      out[argv[i].slice(2)] = argv[i + 1] ?? '';
      i += 1;
    }
  }
  return out;
}

function resolveAnswerKey(a: Record<string, string>): { path: string; version: AnswerKeyVersion } {
  const here = path.dirname(fileURLToPath(import.meta.url));
  if (a['answer-key-path']) {
    const version = a['answer-key-version'] as AnswerKeyVersion;
    if (!(ANSWER_KEY_VERSIONS as readonly string[]).includes(version)) {
      throw new Error(`--answer-key-version must be one of ${ANSWER_KEY_VERSIONS.join(' | ')}`);
    }
    return { path: a['answer-key-path'], version };
  }
  const version = a['answer-key'] as AnswerKeyVersion;
  if (!(ANSWER_KEY_VERSIONS as readonly string[]).includes(version)) {
    throw new Error(`--answer-key must be one of ${ANSWER_KEY_VERSIONS.join(' | ')}`);
  }
  const file = version === 'orig' ? 'answer-key.json' : 'answer-key-extended.json';
  return { path: path.resolve(here, '../../cr-loop', file), version };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const a = argMap(process.argv.slice(2));
  if (!a['findings-dir']) {
    console.error('aggregate: --findings-dir is required');
    process.exit(1);
  }
  // tool config: prefer --tool-config; fall back to legacy --kg-state.
  const toolContextConfig = a['tool-config']
    ?? (a['kg-state'] ? `KG:${a['kg-state']}` : '');
  if (!toolContextConfig) {
    console.error('aggregate: --tool-config (or legacy --kg-state) is required');
    process.exit(1);
  }
  const ak = resolveAnswerKey(a);
  const { row, breakdown } = aggregate(a['findings-dir'], ak.path, ak.version, {
    experiment: a.experiment,
    hId: a.hypothesis,
    variant: a.variant,
    skillVersion: a['skill-version'],
    model: a.model,
    toolContextConfig,
    baselineF1: a['baseline-f1'] ? Number(a['baseline-f1']) : null,
    cost: a.cost,
    logLink: a['log-link'],
    latency: a.latency,
    tokensPerPr: a['tokens-per-pr'] ? Number(a['tokens-per-pr']) : null,
    annotationCoverage: a['annotation-coverage'] as ExperimentRow['annotationCoverage'],
    seed: a.seed,
  });
  validateExperimentRow(row);
  breakdown.forEach((b) => validateClassBreakdownRow(b));

  const rowJson = JSON.stringify(row, null, 2);
  if (a.out) {
    fs.writeFileSync(a.out, rowJson);
    console.error(`aggregate: wrote ${a.out}`);
  } else {
    console.log(rowJson);
  }
  if (a['breakdown-out']) {
    fs.writeFileSync(a['breakdown-out'], JSON.stringify(breakdown, null, 2));
    console.error(`aggregate: wrote ${a['breakdown-out']} (${breakdown.length} class rows)`);
  }
}
