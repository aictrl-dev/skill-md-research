#!/usr/bin/env npx tsx
/**
 * Aggregate per-PR cr-loop scores for one variant into a single Results row.
 *
 * Reuses cr-loop's trusted score() per PR, then micro-averages: sum TP/FP/FN
 * across PRs and compute precision/recall/F1 from the sums (NOT a mean of
 * per-PR F1s, which would over-weight small PRs).
 *
 * Usage:
 *   npx tsx aggregate.ts --findings-dir <dir> --answer-key <orig|extended> \
 *     --experiment cr-loop --hypothesis H-003 --variant "Phase E" \
 *     --skill-version code-review.SKILL.v3.md --model zai-coding-plan/glm-5.1 \
 *     --kg-state populated [--baseline-f1 0.369] [--cost "46M tok"] \
 *     [--log-link log/004.md] [--out results-row.json]
 *
 * --answer-key orig|extended resolves to cr-loop/answer-key.json or
 * answer-key-extended.json. For tests, pass --answer-key-path + --answer-key-version.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { score, type SkillFinding } from '../../cr-loop/scripts/score.ts';
import {
  type ResultsRow,
  type KgState,
  type AnswerKeyVersion,
  KG_STATES,
  ANSWER_KEY_VERSIONS,
  validateResultsRow,
} from './schema.ts';

const round3 = (n: number): number => Math.round(n * 1000) / 1000;

export interface AggregateMeta {
  experiment: string;
  hId: string;
  variant: string;
  skillVersion: string;
  model: string;
  kgState: KgState;
  baselineF1?: number | null;
  cost?: string;
  logLink?: string;
}

export function aggregate(
  findingsDir: string,
  answerKeyPath: string,
  answerKeyVersion: AnswerKeyVersion,
  meta: AggregateMeta,
): ResultsRow {
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
  }

  const precision = tp + fp === 0 ? 0 : tp / (tp + fp);
  const recall = tp + fn === 0 ? 0 : tp / (tp + fn);
  const f1 = precision + recall === 0 ? 0 : (2 * precision * recall) / (precision + recall);
  const baseline = meta.baselineF1 ?? null;

  return {
    experiment: meta.experiment,
    hId: meta.hId,
    variant: meta.variant,
    skillVersion: meta.skillVersion,
    model: meta.model,
    kgState: meta.kgState,
    answerKeyVersion,
    nPrs: files.length,
    tp: round3(tp),
    fp: round3(fp),
    fn: round3(fn),
    novels,
    precision: round3(precision),
    recall: round3(recall),
    f1: round3(f1),
    deltaF1: baseline === null ? null : round3(f1 - baseline),
    cost: meta.cost ?? '',
    logLink: meta.logLink ?? '',
  };
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
  if (!(KG_STATES as readonly string[]).includes(a['kg-state'])) {
    console.error(`aggregate: --kg-state must be one of ${KG_STATES.join(' | ')}`);
    process.exit(1);
  }
  const ak = resolveAnswerKey(a);
  const row = aggregate(a['findings-dir'], ak.path, ak.version, {
    experiment: a.experiment,
    hId: a.hypothesis,
    variant: a.variant,
    skillVersion: a['skill-version'],
    model: a.model,
    kgState: a['kg-state'] as KgState,
    baselineF1: a['baseline-f1'] ? Number(a['baseline-f1']) : null,
    cost: a.cost,
    logLink: a['log-link'],
  });
  validateResultsRow(row);
  const json = JSON.stringify(row, null, 2);
  if (a.out) {
    fs.writeFileSync(a.out, json);
    console.error(`aggregate: wrote ${a.out}`);
  } else {
    console.log(json);
  }
}
