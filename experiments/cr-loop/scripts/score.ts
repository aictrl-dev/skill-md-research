#!/usr/bin/env npx tsx
/**
 * Score a skill run's findings against the answer key, return F1.
 *
 * Inputs:
 *   - findings file (JSON): { prNumber: <N>, findings: [...] } as produced
 *     by run-review.ts
 *   - experiments/cr-loop/answer-key.json
 *
 * Matching:
 *   - For each labelled finding in the answer key for this PR, search the
 *     skill's findings for a match on (file, severity) with fuzzy line
 *     tolerance (±5).
 *   - Match found → categorise by (verdict, action) of the labelled entry:
 *       TRUE  + FIX   → True Positive (must-have detection)
 *       TRUE  + DEFER → True Positive (out-of-scope but real)
 *       TRUE  + IGNORE → True Positive (real but resolved)
 *       FALSE + IGNORE → False Positive (skill repeating a known-FP claim)
 *       FALSE + FIX   → False Positive
 *       UNCERTAIN/*   → counted half-credit
 *   - Labelled entry NOT matched in skill output → False Negative (missed)
 *   - Skill finding NOT matched in answer key → Novel finding (unscored —
 *     could be a new TP or new FP, needs separate grading; tracked separately
 *     so the metric is conservative).
 *
 * F1 metric:
 *   precision = TP / (TP + FP)        — does the skill avoid false alarms?
 *   recall    = TP / (TP + FN)        — does the skill catch known-real issues?
 *   f1        = 2 * p * r / (p + r)
 *
 * Why this metric: it's the standard precision/recall tradeoff that the
 * code-review domain genuinely cares about. Lower FP rate is what made the
 * "actionable vs noise" framing matter all session; higher recall is what
 * makes the bot worth keeping around. F1 balances them.
 *
 * Usage:
 *   npx tsx experiments/cr-loop/scripts/score.ts --findings <path> [--pr <N>]
 *
 * Exit code: 0 always (this is a measurement, not a gate).
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const ANSWER_KEY_PATH = path.join(ROOT, process.env.CR_LOOP_ANSWER_KEY ?? 'answer-key.json');

const LINE_TOLERANCE = 5; // fuzzy match for line-number drift between review SHAs

interface AnswerKeyEntry {
  bot: string;
  severity: string;
  file: string;
  line: string;
  description: string;
  verdict: 'TRUE' | 'FALSE' | 'UNCERTAIN';
  action: 'FIX' | 'DEFER' | 'IGNORE';
  reason: string;
}

interface SkillFinding {
  file: string;
  line?: number | string;
  severity: string;
  title?: string;
  description?: string;
}

interface ScoreResult {
  prNumber: number;
  totals: {
    answerKeySize: number;
    skillFindingsSize: number;
    truePositives: number;
    falsePositives: number;
    falseNegatives: number;
    novelFindings: number;
    halfCredits: number; // UNCERTAIN matches count for 0.5
  };
  precision: number;
  recall: number;
  f1: number;
  notes: {
    matchedAnswerKeyByVerdict: Record<string, number>;
    /** Labelled findings the skill missed — useful for diagnosing recall failures. */
    missed: AnswerKeyEntry[];
    /** Skill findings not in the answer key — could be new TPs or new FPs. */
    novel: SkillFinding[];
  };
}

function parseLineRange(line: string | number | undefined): { start: number; end: number } | null {
  if (line === undefined || line === null || line === '') return null;
  const s = String(line);
  // Accept "123" or "123-127" or "123–127" (em dash from bot output)
  const m = s.match(/^(\d+)(?:[-–](\d+))?$/);
  if (!m) return null;
  const start = parseInt(m[1], 10);
  const end = m[2] ? parseInt(m[2], 10) : start;
  return { start, end };
}

function linesIntersect(a: { start: number; end: number } | null, b: { start: number; end: number } | null): boolean {
  if (!a || !b) return true; // file-level findings (no line) match by file alone
  return Math.abs(a.start - b.start) <= LINE_TOLERANCE || (a.start <= b.end + LINE_TOLERANCE && a.end + LINE_TOLERANCE >= b.start);
}

function severitiesMatch(a: string, b: string): boolean {
  // Normalise: bot uses BLOCKER/MAJOR/MINOR/NIT; skill might use critical/high/medium/low/info
  const norm = (s: string): string => {
    const u = s.toUpperCase();
    // canonicalise sev families
    if (u === 'BLOCKER' || u === 'CRITICAL' || u === 'SECURITY') return 'CRITICAL';
    if (u === 'MAJOR' || u === 'HIGH' || u === 'BUG') return 'HIGH';
    if (u === 'MINOR' || u === 'MEDIUM' || u === 'CONSISTENCY') return 'MEDIUM';
    if (u === 'NIT' || u === 'LOW' || u === 'INFO') return 'LOW';
    return u;
  };
  return norm(a) === norm(b);
}

function matchesAnswerKey(skill: SkillFinding, ak: AnswerKeyEntry): boolean {
  if (skill.file !== ak.file) return false;
  if (!severitiesMatch(skill.severity, ak.severity)) return false;
  return linesIntersect(parseLineRange(skill.line), parseLineRange(ak.line));
}

export function score(prNumber: number, skillFindings: SkillFinding[]): ScoreResult {
  const answerKey = JSON.parse(fs.readFileSync(ANSWER_KEY_PATH, 'utf8')) as Record<string, AnswerKeyEntry[]>;
  const labels = answerKey[String(prNumber)] ?? [];

  const matchedAnswerKey = new Set<number>();
  const matchedSkill = new Set<number>();
  const matchedAnswerKeyByVerdict: Record<string, number> = {};

  // For each skill finding, find its match (if any) in the answer key
  skillFindings.forEach((sf, i) => {
    const matchIdx = labels.findIndex((ak, j) => !matchedAnswerKey.has(j) && matchesAnswerKey(sf, ak));
    if (matchIdx === -1) return;
    matchedAnswerKey.add(matchIdx);
    matchedSkill.add(i);
    const key = `${labels[matchIdx].verdict}/${labels[matchIdx].action}`;
    matchedAnswerKeyByVerdict[key] = (matchedAnswerKeyByVerdict[key] ?? 0) + 1;
  });

  let tp = 0;
  let fp = 0;
  let halfCredits = 0;

  for (const idx of matchedAnswerKey) {
    const ak = labels[idx];
    if (ak.verdict === 'TRUE') tp += 1;
    else if (ak.verdict === 'FALSE') fp += 1;
    else if (ak.verdict === 'UNCERTAIN') {
      tp += 0.5;
      halfCredits += 1;
    }
  }

  // False negatives: TRUE-verdict labels the skill never raised.
  // We only count TRUE/FIX as a hard miss; TRUE/DEFER and TRUE/IGNORE are
  // less load-bearing (real but not actionable in this PR's scope), so they
  // count as half-FN. Pure FALSE-verdict labels not matched = good (skill
  // correctly didn't repeat the FP).
  const missed = labels.filter((_, idx) => !matchedAnswerKey.has(idx));
  let fn = 0;
  for (const m of missed) {
    if (m.verdict !== 'TRUE') continue;
    if (m.action === 'FIX') fn += 1;
    else fn += 0.5;
  }

  // Novel = skill findings with no answer-key match. Not penalised here
  // (could be a new TP), but reported for downstream grading.
  const novel = skillFindings.filter((_, i) => !matchedSkill.has(i));

  const precision = tp + fp === 0 ? 0 : tp / (tp + fp);
  const recall = tp + fn === 0 ? 0 : tp / (tp + fn);
  const f1 = precision + recall === 0 ? 0 : (2 * precision * recall) / (precision + recall);

  return {
    prNumber,
    totals: {
      answerKeySize: labels.length,
      skillFindingsSize: skillFindings.length,
      truePositives: tp,
      falsePositives: fp,
      falseNegatives: fn,
      novelFindings: novel.length,
      halfCredits,
    },
    precision,
    recall,
    f1,
    notes: {
      matchedAnswerKeyByVerdict,
      missed,
      novel,
    },
  };
}

// CLI
function parseArgs(): { findings: string; pr?: number } {
  const args = process.argv.slice(2);
  const findingsIdx = args.indexOf('--findings');
  const prIdx = args.indexOf('--pr');
  if (findingsIdx === -1) {
    console.error('Usage: score.ts --findings <path> [--pr <N>]');
    process.exit(1);
  }
  return {
    findings: args[findingsIdx + 1],
    pr: prIdx === -1 ? undefined : parseInt(args[prIdx + 1], 10),
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const { findings: findingsPath, pr } = parseArgs();
  const data = JSON.parse(fs.readFileSync(findingsPath, 'utf8')) as { prNumber?: number; findings: SkillFinding[] };
  const prNumber = pr ?? data.prNumber;
  if (!prNumber) {
    console.error('Could not determine PR number — pass --pr <N> or include prNumber in the findings file');
    process.exit(1);
  }
  const result = score(prNumber, data.findings);
  console.log(JSON.stringify(result, null, 2));
}
