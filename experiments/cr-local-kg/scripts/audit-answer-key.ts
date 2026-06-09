#!/usr/bin/env npx tsx
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

interface AnswerKeyEntry {
  severity?: string;
  file: string;
  line: string | number;
  description?: string;
  verdict?: string;
  action?: string;
  impact?: string;
}

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXP = path.resolve(HERE, '..');

function normalizeText(s: unknown): string {
  return String(s ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function exactKey(e: AnswerKeyEntry): string {
  return [
    e.file,
    String(e.line ?? ''),
    e.severity ?? '',
    e.verdict ?? '',
    e.action ?? '',
    e.impact ?? '',
    normalizeText(e.description),
  ].join('|');
}

function outcomeKey(e: AnswerKeyEntry): string {
  return [e.severity ?? '', e.verdict ?? '', e.action ?? '', e.impact ?? ''].join('/');
}

export function auditAnswerKey(answerKeyPath: string): { entries: number; duplicates: string[]; conflicts: string[] } {
  const answerKey = JSON.parse(fs.readFileSync(answerKeyPath, 'utf8')) as Record<string, AnswerKeyEntry[]>;
  const duplicates: string[] = [];
  const conflicts: string[] = [];
  let entries = 0;

  for (const [pr, labels] of Object.entries(answerKey)) {
    entries += labels.length;

    const exact = new Map<string, number>();
    labels.forEach((entry, index) => {
      const key = exactKey(entry);
      const first = exact.get(key);
      if (first === undefined) exact.set(key, index);
      else duplicates.push(`PR-${pr} entries ${first} and ${index}: ${entry.file}:${entry.line}`);
    });

    const byLocation = new Map<string, AnswerKeyEntry[]>();
    labels.forEach((entry) => {
      const key = `${entry.file}:${entry.line}`;
      const bucket = byLocation.get(key) ?? [];
      bucket.push(entry);
      byLocation.set(key, bucket);
    });

    for (const [location, bucket] of byLocation) {
      if (bucket.length < 2) continue;
      const outcomes = new Set(bucket.map(outcomeKey));
      const realVsNonReal = new Set(bucket.map((entry) => entry.impact ?? (entry.verdict === 'TRUE' ? 'real' : 'non-real')));
      if (outcomes.size > 1 || realVsNonReal.size > 1) {
        conflicts.push(`PR-${pr} ${location}: ${[...outcomes].join(', ')}`);
      }
    }
  }

  return { entries, duplicates, conflicts };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const answerKeyPath = process.argv[2] ? path.resolve(process.argv[2]) : path.join(EXP, 'answer-key.json');
  const result = auditAnswerKey(answerKeyPath);
  console.log(`answer-key entries: ${result.entries}`);
  console.log(`exact duplicates: ${result.duplicates.length}`);
  for (const duplicate of result.duplicates) console.log(`  duplicate: ${duplicate}`);
  console.log(`location conflicts: ${result.conflicts.length}`);
  for (const conflict of result.conflicts) console.log(`  conflict: ${conflict}`);
  if (result.duplicates.length > 0 || result.conflicts.length > 0) process.exitCode = 1;
}
